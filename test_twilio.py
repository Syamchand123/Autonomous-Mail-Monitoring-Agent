import os
from dotenv import load_dotenv
from twilio.rest import Client

print("--- Starting Twilio Connection Test ---")
load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp_number = os.getenv("TWILIO_PHONE_NUMBER")
to_whatsapp_number = os.getenv("MY_PHONE_NUMBER")

# --- VERIFICATION ---
print(f"Account SID: {account_sid}")
print(f"Auth Token: {'*' * len(auth_token) if auth_token else 'Not Found'}")
print(f"From Number: {from_whatsapp_number}")
print(f"To Number:   {to_whatsapp_number}")

if not all([account_sid, auth_token, from_whatsapp_number, to_whatsapp_number]):
    print("\nERROR: One or more Twilio variables are missing in your .env file. Please check them.")
else:
    try:
        print("\nAttempting to send a test message...")
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body="Hello from your Python Agent! If you received this, the Twilio connection is working.",
            from_=from_whatsapp_number,
            to=to_whatsapp_number
        )
        
        print(f"\nSUCCESS! Message sent successfully. SID: {message.sid}")
        
    except Exception as e:
        print(f"\nERROR: The test failed. Twilio returned an error: {e}")

print("\n--- Test Complete ---")