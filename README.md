# Autonomous Placement Prep Agent 🤖

A sophisticated AI agent designed to fully automate the tedious workflow of monitoring, analyzing, and preparing for university placement opportunities. This agent acts as a personal assistant, turning hours of manual work into a seamless, automated background process.


---


![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)
![Google Cloud](https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud)
![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio)



---

### Table of Contents
1.  [The Problem](#the-problem-)
2.  [The Solution](#the-solution-)
3.  [Core Features](#-core-features)
4.  [System Workflow](#-system-workflow)
5.  [Tech Stack](#-tech-stack)
6.  [Setup & Configuration](#-setup--configuration)
7.  [Usage](#-usage)
8.  [Project Roadmap](#-project-roadmap)

---
### The Problem 😫
The placement season for any student is a period of high stress and information overload. My inbox was flooded with dozens of emails about job opportunities, test schedules, and company announcements. Manually tracking deadlines, researching each company, and preparing for interviews was time-consuming, repetitive, and prone to human error. I needed a way to automate this entire process.

### The Solution ✨
I engineered the **Autonomous Placement Prep Agent**, a smart system that acts as my personal secretary. It runs 24/7 in the background, reads my emails, understands them using AI, and takes action. It organizes my schedule, does my initial research, and delivers a concise, actionable preparation guide directly to my phone, ensuring I never miss an opportunity and can focus my energy on what truly matters: preparing for the interviews.

---

### ⭐ Core Features
*   **🧠 AI-Powered Analysis:** Leverages Google's Gemini LLM to perform advanced NLP for classifying emails (New Opportunity, Test Schedule, etc.) and extracting key entities like company names, deadlines, roles, and CTC.
*   **📅 Automatic Calendar Integration:** Connects to the Google Calendar API to create events for application deadlines and interview dates, complete with custom reminders.
*   **🌐 Autonomous Web Research:** Performs targeted web scraping of high-quality sources (GeeksforGeeks, Glassdoor) to gather intelligence on company interview processes, frequently asked questions, and key topics.
*   **📝 AI-Synthesized Prep Guides:** Synthesizes the messy, scraped web data into a clean, structured, and comprehensive preparation report.
*   **📱 Instant WhatsApp Notifications:** Delivers a concise summary of the opportunity and the full, multi-part preparation guide directly via the Twilio API.
*   **⚙️ Resilient & Autonomous:** Deployed as a scheduled background task, ensuring it runs reliably every hour with built-in error handling and rate-limit management.

---

### 🌊 System Workflow
The agent operates on a continuous **Perceive-Think-Act** cycle:

1.  **Perceive:** Every hour, the agent connects to the **Gmail API** to scan for new, unread emails from the placement cell.
2.  **Think (Analysis):** The body of each new email is sent to the **Google Gemini LLM**. The AI analyzes the unstructured text and returns a structured JSON object, classifying the email's intent and extracting all relevant data.
3.  **Act (Tier 1):**
    *   If the email contains deadlines or interview dates, the agent uses the **Google Calendar API** to create corresponding events.
    *   If the email is a "New Opportunity," it triggers the next stage of action.
4.  **Think (Research & Synthesis):**
    *   The agent uses the extracted company name to perform targeted web scraping, prioritizing trusted sources.
    *   All the scraped text is then passed back to the **Google Gemini LLM** with a detailed prompt asking it to act as a "placement mentor" and generate a high-quality prep guide.
5.  **Act (Tier 2):**
    *   The final report is sent via the **Twilio API** as a series of WhatsApp messages.
    *   Finally, the agent uses the **Gmail API** to mark the original email as "read," completing the cycle.

---

### 💻 Tech Stack
| Category          | Technology / Service                                                                                      |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| **Core Language**   | Python                                                                                                    |
| **AI & NLP**        | Google Gemini Pro                                                                                         |
| **Google Services** | Google Cloud Platform, Gmail API, Google Calendar API                                                     |
| **Notifications**   | Twilio API for WhatsApp                                                                                   |
| **Web Scraping**    | DuckDuckGo Search, BeautifulSoup, Requests                                                                |
| **Deployment**      | Windows Task Scheduler (as a background service)                                                          |
| **Libraries**       | `google-api-python-client`, `google-auth-oauthlib`, `python-dotenv`, `twilio`, etc.                       |


