# Autonomous-Mail-Monitoring-Agent

**A personal AI agent that fully automates the workflow of monitoring, analyzing, and preparing for university placement opportunities.**

---


## 🤖 About The Project

This project was born out of the need to manage the overwhelming number of job opportunity emails received during the placement season. I developed this autonomous agent to turn hours of manual work—reading emails, tracking deadlines, and researching companies—into a fully automated background process.

The agent perceives new emails, uses an AI pipeline to understand their content, takes actions like creating calendar events, and acts as a research assistant to generate detailed preparation guides.

## ✨ Key Features

*   **Automated Email Parsing:** Connects to the Gmail API to find and read new, unread job opportunity emails.
*   **AI-Powered Analysis:** Uses Google's Gemini LLM to perform Natural Language Processing, classifying emails (New Opportunity, Test Schedule, etc.) and extracting key entities like company names, deadlines, roles, and CTC.
*   **Automatic Calendar Integration:** Creates events in Google Calendar for application deadlines and interview dates.
*   **Autonomous Web Research:** Performs targeted web scraping of high-quality sources (like GeeksforGeeks and Glassdoor) to gather intelligence on company interview processes.
*   **AI-Synthesized Prep Guides:** Uses the scraped data to generate comprehensive, structured preparation reports covering the recruitment process, key topics, and frequently asked questions.
*   **Push Notifications:** Delivers a summary of the opportunity and the full report directly to my phone via WhatsApp using the Twilio API.
*   **Resilient & Autonomous:** Deployed as a scheduled background task on Windows, ensuring it runs reliably every hour without manual intervention.

## 🛠️ Tech Stack

*   **Core Language:** Python
*   **AI & NLP:** Google Gemini
*   **Google Services:** Gmail API, Google Calendar API
*   **Notifications:** Twilio API for WhatsApp
*   **Web Scraping:** DuckDuckGo Search, BeautifulSoup, Requests
*   **Deployment:** Windows Task Scheduler
