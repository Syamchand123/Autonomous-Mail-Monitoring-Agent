import os
import os.path
import base64
import google.generativeai as genai
import time
import math

from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests


from dotenv import load_dotenv
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from twilio.rest import Client

# -- SETUP --
# This function loads the variables from our .env file
load_dotenv() 


# --- SETUP continued ---
# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Define the SCOPES. This is what we are asking the user to allow.
# If you modify these, you'll need to delete token.json and re-authenticate.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",      # See, but not change, emails
    "https://www.googleapis.com/auth/calendar"             # Full access to calendar events
]

def authenticate_google():
    """
    Handles the user authentication flow with Google.
    - If a valid token.json exists, it uses it.
    - If not, it prompts the user to log in and saves the new token.
    Returns:
        gmail_service: An authenticated service object for Gmail.
        calendar_service: An authenticated service object for Calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    # It's created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials expired. Refreshing...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Starting authentication...")
            # This uses the credentials.json file we downloaded
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            print("Credentials saved to token.json.")

    try:
        # Build the service objects to interact with the APIs
        gmail_service = build("gmail", "v1", credentials=creds)
        calendar_service = build("calendar", "v3", credentials=creds)
        print("Successfully authenticated with Google.")
        return gmail_service, calendar_service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None, None



def get_email_body(payload):
    """
    Recursively search for the plain text part of an email.
    Emails can be nested. This function will dig through the parts
    to find the 'text/plain' content and decode it from Base64.
    """
    if "parts" in payload:
        for part in payload["parts"]:
            # A recursive call to dig deeper
            body_data = get_email_body(part)
            if body_data:  # If we found something in the recursive call, return it
                return body_data
    # If the part is the one we're looking for
    if payload.get("mimeType") == "text/plain" and "body" in payload and "data" in payload["body"]:
        # The data is Base64 encoded, so we need to decode it
        data = payload["body"]["data"]
        # Replace special URL-safe characters and decode
        return base64.urlsafe_b64decode(data.replace("-", "+").replace("_", "/")).decode("utf-8")
    return None # Return None if no plain text part is found




def check_emails(gmail_service):
    """
    Checks for unread emails matching the placement criteria.
    Returns:
        A list of email messages that match the query.
    """
    try:
        # --- CUSTOMIZE YOUR GMAIL QUERY HERE ---
        # This query searches for unread emails from a specific sender OR with specific subject keywords.
        # Use "OR" in all caps.
        # Example: "is:unread from:placements@yourcollege.edu"
        # Example: "is:unread subject:(Hiring OR Opportunity OR Job)"
        date_2_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y/%m/%d')
        date__limit = (datetime.now() - timedelta(days=2)).strftime('%Y/%m/%d')
        #query = "is:unread after:{date_2_days_ago} unread from:'Helpdesk CDC' via VITIANS CDC Group, Vellore and Chennai Campus <vitianscdc2026@vitstudent.ac.in>"
        #query = "is:unread from:vitianscdc2026@vitstudent.ac.in"
        query = f"is:unread from:vitianscdc2026@vitstudent.ac.in after:{date__limit}"
        print(f"\nSearching for emails with query: '{query}'")

        # Call the Gmail API to search for messages
        result = gmail_service.users().messages().list(userId="me", q=query).execute()
        messages = result.get("messages", []) # .get() is safer than [], avoids errors if no messages

        if not messages:
            print("No new placement emails found.")
            return []
        else:
            print(f"Found {len(messages)} new email(s). Fetching details...")
            email_list = []
            for message in messages:
                msg = gmail_service.users().messages().get(userId="me", id=message["id"], format='full').execute()
                
                # Use our new helper function to get the decoded body
                email_body = get_email_body(msg["payload"])

                if email_body:
                    email_data = {
                        "id": message["id"],
                        "snippet": msg["snippet"],
                        "body": email_body
                    }
                    email_list.append(email_data)
                else:
                    print(f"Could not find a parsable text body for email ID: {message['id']}. Skipping.")
            return email_list

    except HttpError as error:
        print(f"An error occurred while checking emails: {error}")
        return []

    except Exception as e:
        # A common issue is the email body not being where we expect it.
        # This is a general catch-all for other potential problems.
        print(f"An unexpected error occurred: {e}")
        # A more robust solution would inspect the email structure here.
        return []




def extract_details_with_gemini(email_body):
    """
    Uses Gemini AI to extract structured data from an email body.
    Returns a dictionary with the details, or None if it's not a job opportunity.
    """
    print("  -> Contacting Gemini AI to analyze email...")

    # Set up the model
    generation_config = {
      "temperature": 0.2,
      "top_p": 1,
      "top_k": 1,
      "max_output_tokens": 2048,
    }
    #model = genai.GenerativeModel(model_name="gemini-pro", generation_config=generation_config)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", generation_config=generation_config)
    # This is the "prompt". It's the instruction we give to the AI.
    # It's the most important part of this function.
    prompt = f"""
    You are an intelligent assistant for a B.Tech student. Analyze the following email from the college's placement cell and classify it. Extract key information in a clean JSON format.

    First, determine the "email_type". It can be one of the following:
    - "New Opportunity": A new job or internship announcement.
    - "Test Schedule": Information about an upcoming test, exam, or assessment.
    - "Selection List": A list of students who have been shortlisted or selected.
    - "Tech Talk": An announcement for a webinar, seminar, or tech talk.
    - "General Notification": Any other administrative message (e.g., 'fill this form', 'update your profile').
    - "Other": If it doesn't fit any of the above.

    Based on the type, extract the following details. If a field is not present, use null.

    1. If "email_type" is "New Opportunity":
       - "company_name": string
       - "job_role": string
       - "ctc_or_stipend": string
       - "application_deadline": string (in "YYYY-MM-DD" format)
       - "interview_or_test_date": string (in "YYYY-MM-DD" format. Extract any mentioned dates for tests, interviews, or company visits)
       - "eligibility_criteria": string

    2. If "email_type" is "Test Schedule":
       - "company_name": string
       - "job_role": string (if mentioned)
       - "test_date_time": string (in ISO 8601 format, e.g., "2025-04-05T15:00:00")
       - "test_duration": string (e.g., "30 minutes")
       - "test_location_or_mode": string (e.g., "Virtual", "PRP 713")

    3. If "email_type" is "Selection List":
       - "company_name": string
       - "round_name": string (e.g., "Interview Shortlist", "Final Selection")
       
    4. If "email_type" is "Tech Talk":
       - "topic": string
       - "speaker_or_company": string
       - "date_time": string (in ISO 8601 format)
       - "venue": string

    Do not add any explanation outside of the JSON object.

    Here is the email text:
    ---
    {email_body}
    ---
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up the response to make it valid JSON
        json_response = response.text.strip().replace("```json", "").replace("```", "")
        
        # We need to import the json library to parse this string
        import json
        details = json.loads(json_response)
        
        print(f"  -> Gemini analysis complete. Is opportunity: {details.get('is_opportunity')}")
        return details

    except Exception as e:
        print(f"  -> An error occurred during Gemini analysis: {e}")
        return None




def create_calendar_events(calendar_service, details):
    """
    Creates Google Calendar events based on the extracted details.
    """
    email_type = details.get("email_type")
    
    # --- Event for a New Opportunity Deadline ---
    if email_type == "New Opportunity":
        if  details.get("application_deadline"):
         deadline_str = details["application_deadline"]
        try:
            # The AI should return YYYY-MM-DD format, which works for all-day events.
            event_date = datetime.strptime(deadline_str, "%Y-%m-%d").strftime("%Y-%m-%d")
            
            event = {
                "summary": f"Apply for {details.get('company_name', 'Unknown Company')}",
                "description": f"Role: {details.get('job_role', 'N/A')}\nCTC/Stipend: {details.get('ctc_or_stipend', 'N/A')}\nEligibility: {details.get('eligibility_criteria', 'N/A')}",
                "start": {"date": event_date, "timeZone": "Asia/Kolkata"},
                "end": {"date": event_date, "timeZone": "Asia/Kolkata"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 24 * 60}, # 1 day before
                        {"method": "popup", "minutes": 2 * 24 * 60}, # 2 days before
                    ],
                },
            }
            created_event = calendar_service.events().insert(calendarId="primary", body=event).execute()
            print(f"  -> Successfully created calendar event for deadline: {created_event.get('htmlLink')}")
        except ValueError:
            print(f"  -> Could not parse deadline date: {deadline_str}. Not creating event.")
        except Exception as e:
            print(f"  -> An error occurred creating calendar event: {e}")
            
       
        if details.get("interview_or_test_date"):
         date_str = details["interview_or_test_date"]
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
            event = {
                "summary": f"Interview/Test: {details.get('company_name', 'Unknown Company')}",
                "description": f"Check email for specific timings and details for the {details.get('job_role', 'N/A')} role.",
                "start": {"date": event_date, "timeZone": "Asia/Kolkata"},
                "end": {"date": event_date, "timeZone": "Asia/Kolkata"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 24 * 60},
                    ],
                },
            }
            created_event = calendar_service.events().insert(calendarId="primary", body=event).execute()
            print(f"  -> Successfully created calendar event for interview/test date: {created_event.get('htmlLink')}")
        except ValueError:
            print(f"  -> Could not parse interview/test date: {date_str}. Not creating event.")
        except Exception as e:
            print(f"  -> An error occurred creating interview/test event: {e}")


    # --- Event for a Test Schedule ---
    elif email_type == "Test Schedule" and details.get("test_date_time"):
        datetime_str = details["test_date_time"]
        try:
            # The AI should return ISO 8601 format (e.g., 2025-04-05T15:00:00)
            start_time = datetime.fromisoformat(datetime_str)
            # Let's assume a 1-hour duration if not specified
            end_time = start_time + timedelta(hours=1)

            event = {
                "summary": f"Test: {details.get('company_name', 'Unknown Company')}",
                "location": details.get("test_location_or_mode", "Check Email"),
                "description": f"Role: {details.get('job_role', 'N/A')}\nDuration: {details.get('test_duration', 'N/A')}",
                "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Kolkata"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 60}, # 1 hour before
                        {"method": "popup", "minutes": 24 * 60}, # 1 day before
                    ],
                },
            }
            created_event = calendar_service.events().insert(calendarId="primary", body=event).execute()
            print(f"  -> Successfully created calendar event for test: {created_event.get('htmlLink')}")

        except ValueError:
            print(f"  -> Could not parse test date/time: {datetime_str}. Not creating event.")
        except Exception as e:
            print(f"  -> An error occurred creating calendar event: {e}")





def mark_as_read(gmail_service, email_id):
    """
    Marks an email as read by removing the 'UNREAD' label.
    """
    try:
        # The request body to modify the labels.
        body = {"removeLabelIds": ["UNREAD"]}
        gmail_service.users().messages().modify(userId="me", id=email_id, body=body).execute()
        print(f"  -> Successfully marked email {email_id} as read.")
    except HttpError as error:
        print(f"  -> An error occurred while marking email as read: {error}")








def generate_prep_report(company_name, job_role):
    """
    Researches a company and job role and generates a prep report using AI.
    """
    print(f"  -> Starting research for {job_role} at {company_name}...")
    
    # --- Step 1: Perform targeted web searches ---
    print("  -> Performing targeted web searches...")
    search_queries = [
        f"'{company_name}' '{job_role}' interview experience geeksforgeeks", # High-quality source
        f"'{company_name}' technical interview questions glassdoor",  # Good for specific questions
        f"'{company_name}' '{job_role}' recruitment process",
        f"'{company_name}' compensation details",
        f"site:leetcode.com '{company_name}' '{job_role}' interview",
        f"'{company_name}' '{job_role}' interview process",
        f"'{company_name}' '{job_role}' interview questions",
        f"what is it like to work at '{company_name}'",
        f"'{company_name}' company culture"# Search LeetCode specifically
    ]
    
    raw_text_content = ""
    print("  -> Gathering information from the web...")
    
    with DDGS() as ddgs:
        for query in search_queries:
            # Get top 3 results for each query
            search_results = list(ddgs.text(query, max_results=3))
            for result in search_results:
                try:
                    print(f"    -> Scraping: {result['href']}")
                    # Use a user-agent to pretend we are a real browser
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
                    response = requests.get(result['href'], headers=headers, timeout=10)
                    
                    # Use BeautifulSoup to parse the HTML and get only the text
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Get all the text from the body tag
                    body_text = soup.body.get_text(separator=' ', strip=True)
                    raw_text_content += body_text + "\n\n"
                    # Add a small delay to be polite to the websites
                    time.sleep(1)
                except Exception as e:
                    print(f"    -> Could not scrape {result['href']}. Error: {e}")
    
    if not raw_text_content:
        print("  -> Could not gather any information from the web. Aborting report.")
        return "Could not generate a report. Failed to gather information online."

    # --- Step 2: Synthesize a Report with Gemini ---
    print("  -> Synthesizing research into a report with Gemini AI...")
    
    '''report_prompt = f"""
    You are an expert career coach. Based on the following raw, messy text scraped from various websites, create a concise and structured preparation report for a student applying for the '{job_role}' role at '{company_name}' for oncampus placement in b.tech final year.

    The report MUST have the following sections, clearly marked:
    1.  **About the Company:** A brief, one-paragraph overview of what the company does.
    2.  **The Recruitment Process:** A bulleted or numbered list of the typical interview stages (e.g., Online Assessment, Technical Round 1, HR Round,Any other stage if applicable e.g., Technical Round 2 or group discussion).
    3.  **Key Technical Topics to Prepare:** A bulleted list of the most important technical skills, programming languages, or concepts mentioned in the text.
    4.  **Common Interview Questions:** A list of 10-15 sample interview questions (technical or behavioral) that were found in the text.
    5.  **Company Culture & Work Environment:** A short paragraph summarizing the work culture.

    Do not invent information. Base your report ONLY on the provided text. If the text for a section is poor or missing, just write "Information not available in the provided text."

    Here is the raw text:
    ---
    {raw_text_content[:10000]} 
    ---
    """ # We truncate the text to stay within context limits'''
    
    report_prompt = f"""
    You are a helpful senior from the student's college, acting as a placement preparation mentor. Your task is to analyze the following raw text scraped from websites like GeeksforGeeks, Glassdoor, and others. Create a detailed, well-structured, and encouraging preparation guide for a student applying for the '{job_role}' role at '{company_name}'.

    The report MUST be comprehensive and have the following sections, clearly marked with markdown formatting (e.g., **bold**, *italics*, and bullet points).

    ---
    ### 🚀 Prep Guide for: {company_name} - {job_role} 🚀
    ---

    **1. About The Company & The Role**
    *   Briefly describe what '{company_name}' does and what the '{job_role}' likely entails based on the scraped text. Mention the company's main products or industry.

    **2. The Recruitment Process (All Stages)**
    *   Based on the interview experiences found, create a step-by-step list of the typical recruitment stages. Be specific. For example:
        *   *Stage 1: Online Assessment:* (Mention platforms like HackerRank/AMCAT, types of questions like MCQs, Coding, etc.)
        *   *Stage 2: Technical Interview 1:* (Mention focus areas like Data Structures, Algorithms, Core Subjects, etc.)
        *   *Stage 3: Technical Interview 2 (if applicable):* (Mention deeper dives, project discussions, etc.)
        *   *Stage 4: HR / Managerial Round:* (Mention behavioral questions, cultural fit, etc.)

    **3. 🎯 Key Technical Topics to Prepare**
    *   This is the most important section. Create a detailed, bulleted list of the most critical topics to study. Group them by category.
    *   **Data Structures & Algorithms:** (e.g., Arrays, Strings, Trees, Graphs, Sorting, Dynamic Programming).
    *   **Core Subjects:** (e.g., Operating Systems, DBMS, Computer Networks, OOPS Concepts).
    *   **Languages & Frameworks:** (e.g., Python, C++, Java, React, NodeJS - whatever was mentioned).
    *   **System Design (if applicable):** (Mention if system design questions are asked for this role).

    **4. ❓ Frequently Asked Interview Questions**
    *   List 5-7 specific and high-quality technical or behavioral questions that were mentioned in the scraped text.
    *   For at least one coding question, provide a brief hint or approach on how to solve it.
        *   *Example Question:* "Find the middle of a linked list." -> *Hint: Use the "fast and slow pointer" approach.*
        *   *Example Question:* "Tell me about a challenging project you worked on."

    **5. Final Tips & Words of Encouragement**
    *   End with a positive and encouraging paragraph. Wish the student good luck.

    ---
    *Disclaimer: This report is AI-generated based on publicly available data and may not be 100% accurate. Always cross-verify with official sources.*
    ---

    **RAW SCRAPED TEXT FOR ANALYSIS:**
    {raw_text_content[:15000]} 
    """ # Increased context length slightly

    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
        response = model.generate_content(report_prompt)
        print("  -> Report generated successfully.")
        return response.text
    except Exception as e:
        print(f"  -> An error occurred during report synthesis: {e}")
        return f"An error occurred while generating the report: {e}"




'''def send_whatsapp_notification(report, details):
    """
    Sends a notification with the prep report to your WhatsApp.
    """
    print("  -> Sending report to WhatsApp...")
    
    # Load credentials from .env file
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp_number = os.getenv("TWILIO_PHONE_NUMBER")
    to_whatsapp_number = os.getenv("MY_PHONE_NUMBER")
    
    #
    # --- VERIFICATION STEP ---
    #
    if not all([account_sid, auth_token, from_whatsapp_number, to_whatsapp_number]):
        print("  -> ERROR: Twilio credentials not found in .env file.")
        print("  -> Please check TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, and MY_PHONE_NUMBER.")
        return # Stop the function if credentials are missing
    
    try:
        client = Client(account_sid, auth_token)

        # --- Message 1: The Summary ---
        # This message gives a quick, readable overview of the opportunity.
        summary_message = (
            f"🚀 *New Opportunity Found!* 🚀\n\n"
            f"*Company:* {details.get('company_name', 'N/A')}\n"
            f"*Role:* {details.get('job_role', 'N/A')}\n"
            f"*CTC/Stipend:* {details.get('ctc_or_stipend', 'N/A')}\n"
            f"*Apply By:* {details.get('application_deadline', 'N/A')}\n"
            f"*Test/Interview:* {details.get('interview_or_test_date', 'N/A')}\n\n"
            f"I've added events to your calendar. The full AI-generated prep report is in the next message. Good luck!"
        )
        
        # Send the first message
        message1 = client.messages.create(
            body=summary_message,
            from_=from_whatsapp_number,
            to=to_whatsapp_number
        )
        print(f"  -> Summary message sent successfully (SID: {message1.sid}).")
        
        # Add a small delay between messages to ensure they arrive in order
        time.sleep(3)

        # --- Message 2: The Full Report ---
        # WhatsApp has a character limit, so we must be careful.
        full_report_message = "📄 *AI-Generated Preparation Report* 📄\n\n" + report
        if len(full_report_message) > 1600: # WhatsApp's character limit
            full_report_message = full_report_message[:1550] + "\n\n*[Report truncated due to length]*"

        # Send the second message
        message2 = client.messages.create(
            body=full_report_message,
            from_=from_whatsapp_number,
            to=to_whatsapp_number
        )
        
        print(f"  -> Report message sent successfully (SID: {message2.sid}).")

    except Exception as e:
        print(f"  -> An error occurred while sending WhatsApp notification: {e}")'''

def send_whatsapp_notification(report, details):
    """
    Sends a notification with the prep report to your WhatsApp.
    If the report is long, it intelligently splits it into multiple messages.
    """
    print("  -> Sending detailed report to WhatsApp...")
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp_number = os.getenv("TWILIO_PHONE_NUMBER")
    to_whatsapp_number = os.getenv("MY_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, from_whatsapp_number, to_whatsapp_number]):
        print("  -> ERROR: Twilio credentials not found in .env file. Skipping WhatsApp notification.")
        return

    try:
        client = Client(account_sid, auth_token)

        # --- Message 1: The Summary ---
        summary_message = (
            f"🚀 *New Opportunity Found!* 🚀\n\n"
            f"*Company:* {details.get('company_name', 'N/A')}\n"
            f"*Role:* {details.get('job_role', 'N/A')}\n"
            f"*CTC/Stipend:* {details.get('ctc_or_stipend', 'N/A')}\n"
            f"*Apply By:* {details.get('application_deadline', 'N/A')}\n"
            f"*Test/Interview:* {details.get('interview_or_test_date', 'N/A')}\n\n"
            f"I've added events to your calendar. The full AI-generated prep report will follow in the next message(s). Good luck!"
        )
        client.messages.create(body=summary_message, from_=from_whatsapp_number, to=to_whatsapp_number)
        print("  -> Summary message sent successfully.")
        time.sleep(2) # A small pause to ensure messages arrive in order

        # --- Message 2 onwards: The Full Report (with splitting logic) ---
        
        # We need a buffer for the "Part x/y" header
        header_buffer = 50 
        char_limit = 1600 - header_buffer 

        # Check if the report body itself needs to be split
        if len(report) > char_limit:
            print(f"  -> Report is long ({len(report)} chars). Splitting into multiple parts.")
            # Calculate how many chunks we'll need
            num_parts = math.ceil(len(report) / char_limit)
            
            for i in range(num_parts):
                start = i * char_limit
                end = start + char_limit
                chunk = report[start:end]
                
                part_header = f"📄 *Prep Report [Part {i+1}/{num_parts}]* 📄\n\n"
                message_part = part_header + chunk
                
                client.messages.create(body=message_part, from_=from_whatsapp_number, to=to_whatsapp_number)
                print(f"  -> Sent report part {i+1}/{num_parts}.")
                time.sleep(3) # Wait a bit longer between large message parts
        else:
            # If the report is short enough, send as a single message
            full_report_message = "📄 *AI-Generated Preparation Report* 📄\n\n" + report
            client.messages.create(body=full_report_message, from_=from_whatsapp_number, to=to_whatsapp_number)
            print("  -> Report sent successfully in a single message.")

    except Exception as e:
        print(f"  -> An error occurred while sending WhatsApp notification: {e}")



# --- This is the main execution block ---
# We will build this out in later steps. For now, we just test the authentication.    
'''if __name__ == "__main__":
    print("--- Starting Placement Agent ---")
    gmail_service, calendar_service = authenticate_google()

    if not gmail_service or not calendar_service:
        print("\nCould not start agent due to authentication failure.")
    else:
        print("\nAgent is ready. Checking for new opportunities...")
        new_emails = check_emails(gmail_service)
        
        if not new_emails:
            print("No new emails to process.")
        else:
            print(f"\nFound {len(new_emails)} new emails. Analyzing with AI...")
            for email in new_emails:
                print("\n" + "="*50)
                print(f"--- Processing Email ID: {email['id']} ---")
                
                # Step 1: Extract details using Gemini AI
                extracted_details = extract_details_with_gemini(email['body'])
                
                # Step 2: Check if AI found it to be a valid opportunity
                if extracted_details and extracted_details.get("is_opportunity"):
                    print("  -> VALID OPPORTUNITY FOUND!")
                    print("  -> Details:", extracted_details)
                    
                    # TODO: In the next steps, we will call:
                    # create_calendar_events(calendar_service, extracted_details)
                    # report = generate_prep_report(extracted_details['company_name'], extracted_details['job_role'])
                    # send_whatsapp_notification(report, extracted_details)
                else:
                    print("  -> This email is not a new job opportunity. Skipping.")
                
                print("="*50)

    print("\n--- Agent run complete. ---")'''
    
    
# --- This is the main execution block ---
if __name__ == "__main__":
    print("--- Starting Placement Agent ---")
    gmail_service, calendar_service = authenticate_google()

    if not gmail_service or not calendar_service:
        print("\nCould not start agent due to authentication failure.")
    else:
        print("\nAgent is ready. Checking for new emails...")
        new_emails = check_emails(gmail_service)
        
        if not new_emails:
            print("No new emails to process.")
        else:
            print(f"\nFound {len(new_emails)} new emails. Analyzing with AI...")
            for email in new_emails:
                print("\n" + "="*50)
                print(f"--- Processing Email ID: {email['id']} ---")
                
                # Step 1: Extract and categorize details using Gemini AI
                extracted_details = extract_details_with_gemini(email['body'])
                
                
                # Step 2: Handle the email based on its categorized type
                if extracted_details and "email_type" in extracted_details:
                    email_type = extracted_details["email_type"]
                    print(f"  -> AI classified this email as: '{email_type}'")
                    print("  -> Details:", extracted_details)
                    
                    # We will add actions here in the next steps
                    if email_type in ["New Opportunity", "Test Schedule"]:
                        create_calendar_events(calendar_service, extracted_details)
                    
                    if email_type == "New Opportunity":
                        # TODO: In the next steps, we will call:
                        # report = generate_prep_report(...)
                        # send_whatsapp_notification(...)
                        #pass # 'pass' is a placeholder for now
                        company = extracted_details.get("company_name")
                        role = extracted_details.get("job_role")
                        
                        
                        if not role:
                            print("  -> Job role not specified. Using a general research query.")
                            # Use a better, more generic default as you suggested
                            role = f"campus recruitment for freshers"
                            
                        if company and role:
                            prep_report = generate_prep_report(company, role)
                            print("\n--- PREPARATION REPORT ---")
                            print(prep_report)
                            print("--- END OF REPORT ---\n")
                            # TODO: Send this report to WhatsApp
                            send_whatsapp_notification(prep_report, extracted_details)
                         
                         
                        else:
                            print("  -> Could not generate report: Company or Role missing.")
                    
                    elif email_type == "Selection List":
                        print("  -> ACTION: (Future) Send a simple WhatsApp notification.")
                    
                    else:
                        print("  -> ACTION: Logging for information. No action needed.")

                else:
                    print("  -> AI could not categorize this email. Skipping.")
                   
                # Step 3: Mark the email as read 
                mark_as_read(gmail_service, email['id'])
                print("  -> Pausing for 5 seconds...")
                time.sleep(5) 
                print("="*50)

    print("\n--- Agent run complete. ---")