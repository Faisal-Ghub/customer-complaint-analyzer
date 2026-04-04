import streamlit as st
import pdfplumber
import json
import re
import pandas as pd
import requests
from groq import Groq

# ---- Credentials via st.secrets ----
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
N8N_WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]

client = Groq(api_key=GROQ_API_KEY)

st.title("Customer Complaint Analyzer")

# ============================================================
# PHASE 1 — Upload PDF & Extract Text
# ============================================================
st.header("1. Upload Complaint Files")

uploaded_files = st.file_uploader(
    "Upload one or more complaint files (PDF only)",
    type=["pdf"],
    accept_multiple_files=True
)

if "ai_outputs" not in st.session_state:
    st.session_state["ai_outputs"] = []

if "all_complaints" not in st.session_state:
    st.session_state["all_complaints"] = []

if "last_ai_data" not in st.session_state:
    st.session_state["last_ai_data"] = {}

if "last_cleaned_text" not in st.session_state:
    st.session_state["last_cleaned_text"] = ""

all_complaints = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        all_text = ""
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"

            cleaned_text = " ".join(all_text.split())
            st.success(f"Text extracted from: {uploaded_file.name}")
            st.text_area(
                f"Extracted Text: {uploaded_file.name}",
                cleaned_text,
                height=200
            )

        except Exception as e:
            st.error(f"Error extracting text: {e}")
            continue

        # ============================================================
        # PHASE 2 — AI Analysis
        # ============================================================

        issue = "Unknown"
        if "refund" in cleaned_text.lower():
            issue = "Refund request"
        elif "delay" in cleaned_text.lower() or "late" in cleaned_text.lower():
            issue = "Delivery delay"

        prompt = f"""
        You are a customer support analyst.
        Analyze the following complaint and return a JSON with exactly these keys:
        1. "Complaint Category" (Refund, Delivery Delay, Product Issue, Other)
        2. "Priority" (High, Medium, Low)
        3. "Short Summary" (maximum 15 words, concise)
        4. "risk_level" (High, Medium, Low) — same as Priority
        5. "Customer Name" (extract from text, if not found return "Not found")
        6. "Order ID" (extract any order number or ID from text, if not found return "Not found")

        Complaint Text:
        {cleaned_text}

        Return ONLY a valid JSON object. No explanation, no markdown, no backticks.
        """


        with st.spinner(f"Analyzing {uploaded_file.name}..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )

        ai_output_text = response.choices[0].message.content
        st.session_state.ai_outputs.append(ai_output_text)

        try:
            match = re.search(r"\{.*\}", ai_output_text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group())
            else:
                ai_data = {}
        except:
            ai_data = {}
            
        order_id = ai_data.get("Order ID", "Not found")
        customer_name = ai_data.get("Customer Name", "Not found")
        
        # Save last ai_data and text for webhook use later
        st.session_state["last_ai_data"] = ai_data
        st.session_state["last_cleaned_text"] = cleaned_text

        # Display AI Analysis
        if ai_data:
            with st.expander(f"AI Analysis: {uploaded_file.name}"):
                st.write(f"**Category:** {ai_data.get('Complaint Category', 'Not found')}")
                st.write(f"**Priority:** {ai_data.get('Priority', 'Not found')}")
                st.write(f"**Summary:** {ai_data.get('Short Summary', 'Not found')}")
                if ai_data.get("Priority") == "High":
                    st.markdown(
                        "<span style='color:red'>⚠ High Priority Complaint</span>",
                        unsafe_allow_html=True
                    )

        # ============================================================
        # PHASE 3 — Table Data
        # ============================================================
        all_complaints.append({
            "Order ID": order_id,
            "Customer Name": customer_name,
            "Issue Type": issue,
            "AI Complaint Category": ai_data.get("Complaint Category", "Not found"),
            "Priority": ai_data.get("Priority", "Not found"),
            "Short Summary": ai_data.get("Short Summary", "Not found")
        })

# ============================================================
# PHASE 3 — DataFrame + CSV Download
# ============================================================
if all_complaints:
    df = pd.DataFrame(all_complaints)
    st.subheader("All Structured Complaints")
    st.dataframe(df)

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download All Complaints (CSV)",
        data=csv_data,
        file_name="all_complaints_data.csv",
        mime="text/csv"
    )

# ============================================================
# PHASE 4 + 5 — Manager Alert + n8n Webhook
# ============================================================
st.header("Manager Alert Setup")

if "manager_email" not in st.session_state:
    st.session_state["manager_email"] = ""

manager_email = st.text_input(
    "Enter manager email to send alerts:",
    value=st.session_state["manager_email"]
)
st.session_state["manager_email"] = manager_email

if st.button("Send Alert Mail"):
    if not manager_email:
        st.error("Please enter a valid manager email!")

    elif not st.session_state["last_ai_data"]:
        st.error("Please upload and analyze a PDF first!")

    else:
        ai_data = st.session_state["last_ai_data"]
        cleaned_text = st.session_state["last_cleaned_text"]

        payload = {
            "document_text": cleaned_text,
            "extracted_data": ai_data,
            "priority": ai_data.get("Priority", "Unknown"),
            "risk_level": ai_data.get("risk_level", "Unknown"),
            "category": ai_data.get("Complaint Category", "Unknown"),
            "summary": ai_data.get("Short Summary", ""),
            "recipient_email": manager_email
        }
    
        # This is the integration point between streamlit and n8n workflow
        with st.spinner("Sending to n8n... please wait"):
            try:
                response = requests.post(
                    N8N_WEBHOOK_URL,
                    json=payload,
                    timeout=60
                )
                # Checks if n8n responded successfully 
                if response.status_code == 200:
                    result = response.json()

                    # ============================================================
                    # PHASE 5 — Display 4 Outputs
                    # ============================================================
                    st.header("Results from n8n")

                    # Displays ai_data in a nicely formatted JSON block
                    st.subheader("① Structured Data Extracted")
                    st.json(ai_data)
    
                    # Displays processes response from n8n
                    st.subheader("② Final Analytical Answer")
                    st.write(result.get("final_answer", "Not returned from n8n"))

                    # Displays the email content generated by n8n (based on AI data and template in your workflow).

                    st.subheader("③ Generated Email Body")
                    email_body = result.get("email_body", "Not returned from n8n")
                    st.markdown(email_body, unsafe_allow_html=True)


                    # Reads email status returnded by n8n
                    st.subheader("④ Email Automation Status")
                    status = result.get("email_status", "Unknown")
                    if status == "SENT":
                        st.success("Alert Email Status: SENT ✅")
                    elif status == "NOT SENT":
                        st.warning("Status: Condition Not Met — Email Not Sent")
                    else:
                        st.info(f"Status: {status}")

                else:
                    st.error(f"Webhook failed: {response.status_code}")
                    st.code(response.text)

            except Exception as e:
                st.error(f"Error connecting to n8n: {e}")
