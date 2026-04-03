# 🧾 Customer Complaint Analyzer

An end-to-end AI-powered web application that reads customer complaint PDFs, understands them using a large language model, and automatically alerts the right people via email — all without writing a single line of manual logic for the analysis.

---

## What This Project Does

Most businesses receive complaints in unstructured formats — emails, PDFs, scanned letters. Someone has to read each one, figure out how serious it is, and decide whether to escalate it. This project automates that entire process.

You upload a complaint PDF. The app reads it, sends it to an AI model, and gets back a structured understanding of the complaint — what category it falls under, how urgent it is, and a plain-English summary. If the complaint is serious enough, the system can automatically draft and send an alert email to a manager.

---

## How It Works (Plain English)

### Step 1 — Upload the Complaint
The user uploads one or more complaint PDFs through the web interface. The app extracts all the readable text from each file using a PDF parsing library.

### Step 2 — AI Analysis
The extracted text is sent to a Groq-hosted LLaMA 3.3 model (a large language model). The model is given a specific instruction: analyze this complaint and return a structured JSON response with four fields — complaint category, priority level, a short summary, and risk level.

The app parses this JSON and displays the results directly in the UI. High-priority complaints are flagged with a red warning.

### Step 3 — Structured Table
All analyzed complaints are compiled into a clean table (a pandas DataFrame) showing the order ID, customer name, issue type, AI category, priority, and summary. The user can download this table as a CSV file.

### Step 4 — Manager Alert via n8n
The user enters a manager's email address and clicks "Send Alert Mail." This triggers a POST request to an n8n workflow via a webhook. The n8n workflow:
- Receives the complaint data
- Runs its own AI agent analysis
- Checks a condition (e.g., is this High priority?)
- If yes: drafts an alert email and sends it
- Returns the final answer, email body, and send status back to the Streamlit app

### Step 5 — Four Final Outputs
The app displays four clearly labeled outputs from the n8n response:
1. The structured JSON data extracted from the complaint
2. The final analytical answer from the n8n AI agent
3. The generated email body
4. The email send status (SENT or NOT SENT)

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend / UI | Streamlit |
| PDF Parsing | pdfplumber |
| AI / LLM | Groq API (LLaMA 3.3 70B) |
| Workflow Automation | n8n (self-hosted or cloud) |
| Data Handling | pandas |
| HTTP Requests | requests |
| Deployment | Streamlit Cloud |

---

## Project Structure

```
customer-complaint-analyzer/
│
├── app.py               # Main Streamlit application
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## Setup & Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/Faisal-Ghub/customer-complaint-analyzer.git
cd customer-complaint-analyzer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Secrets (Local)

Create a `.streamlit/secrets.toml` file locally (do **not** push this to GitHub):

```toml
GROQ_API_KEY = "your_groq_api_key_here"
N8N_WEBHOOK_URL = "your_n8n_production_webhook_url_here"
```

### 4. Run Locally

```bash
streamlit run app.py
```

### 5. Deploy to Streamlit Cloud

1. Push `app.py` and `requirements.txt` to your GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. After deployment, open **Manage App → Settings → Secrets**
4. Paste your secrets in TOML format and save
5. The app will reboot automatically with credentials loaded securely

> ⚠️ All credentials are stored via the Streamlit Cloud secrets dashboard.

---

## n8n Workflow Setup

The backend automation runs on n8n. Here is how the workflow is structured:

1. **Webhook Trigger Node** — Listens for POST requests from the Streamlit app
2. **AI Agent Node (Analysis)** — Analyzes the incoming complaint data
3. **IF Node** — Checks whether the complaint meets the alert condition (e.g., High priority)
4. **AI Agent Node (Email Draft)** — Drafts a professional alert email (TRUE branch)
5. **Email Node** — Sends the email to the manager
6. **Set Node** — Packages the final answer, email body, and status into a clean JSON
7. **Respond to Webhook Node** — Returns the packaged JSON back to Streamlit

The workflow must be **activated** and the Production Webhook URL must be stored in Streamlit secrets as `N8N_WEBHOOK_URL`.

---

## Security

- All API keys and webhook URLs are stored using `st.secrets` — never hardcoded in the source code
- The `.streamlit/secrets.toml` file is local only and excluded from version control
- On Streamlit Cloud, secrets are managed through the secure dashboard

---

## Requirements

```
streamlit
pdfplumber
groq
requests
pandas
```

---

## Author

**Faisal** — Built as part of an end-of-course summative evaluation covering AI integration, workflow automation, and cloud deployment.
