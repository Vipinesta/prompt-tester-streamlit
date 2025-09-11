import streamlit as st
import requests, json
from typing import Optional

st.set_page_config(page_title="Prompt Tester — n8n Decomposer", layout="centered")

def call_n8n_webhook(webhook_url: str, payload: dict, auth_header: Optional[str] = None, timeout: int = 30):
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header
    resp = requests.post(webhook_url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return resp.text

st.title("⚡ Prompt Testing Playground")
st.write("Enter a query and hit **Run test**")

with st.form("prompt_form"):
    query = st.text_area("User Query", height=160, placeholder="Enter the query here...")
    submitted = st.form_submit_button("Run test")

if submitted:
    if not query or not query.strip():
        st.error("Please enter a query first.")
    else:
        webhook_url = st.secrets.get("N8N_WEBHOOK_URL")
        auth_header = st.secrets.get("N8N_AUTH_HEADER")  # optional
        if not webhook_url:
            st.error("Webhook URL missing — add N8N_WEBHOOK_URL in secrets.")
        else:
            with st.spinner("Calling n8n..."):
                try:
                    payload = {"query": query}
                    result = call_n8n_webhook(webhook_url, payload, auth_header=auth_header)

                    st.subheader("Structured Output")
                    try:
                        # Some n8n responses wrap inside "output"
                        tasks_data = result.get("output", {}).get("tasks") or result.get("tasks")

                        if tasks_data and isinstance(tasks_data, list):
                            for idx, task in enumerate(tasks_data, start=1):
                                if isinstance(task, dict):
                                    task_text = list(task.values())[0]
                                    st.write(f"Task {idx} - {task_text}")
                                else:
                                    st.write(f"Task {idx} - {task}")
                        else:
                            st.warning("No tasks found in response.")
                    except Exception as e:
                        st.error(f"Error displaying tasks: {e}")

                    st.success("✅ Done")

                except Exception as e:
                    st.error(f"Request failed: {e}")

st.markdown("---")
st.caption("Built for quick prompt testing")
