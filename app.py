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
                        # NEW: support both the old format and the new format.
                        # Old format examples:
                        # { "tasks": [ { "task_id": "...", "description": "...", "order": 1, "input_data": {...}, "dependencies": [] } ] }
                        # or { "output": { "tasks": [...] } }
                        #
                        # New format expected:
                        # { "output": { "tasks": [ { "id": "...", "title": "...", "position": 1, "params": {...}, "depends_on": [] } ] } }
                        #
                        # The code below normalizes either format to a common structure for display.

                        # Extract tasks from possible locations
                        tasks_raw = None
                        if isinstance(result, dict):
                            # prefer output.tasks first
                            tasks_raw = result.get("output", {}).get("tasks")
                            if tasks_raw is None:
                                tasks_raw = result.get("tasks")
                        else:
                            tasks_raw = None

                        if tasks_raw and isinstance(tasks_raw, list):
                            for idx, task in enumerate(tasks_raw, start=1):
                                if isinstance(task, dict):
                                    # Normalization: map both old and new keys to a display form
                                    task_id = task.get("task_id") or task.get("id") or f"t{idx}"
                                    description = task.get("description") or task.get("title") or (
                                        # for dicts with single key:value (older ad-hoc format)
                                        (list(task.values())[0] if len(task) == 1 else None)
                                    )
                                    order = task.get("order") or task.get("position") or idx
                                    input_data = task.get("input_data") or task.get("params") or {}
                                    dependencies = task.get("dependencies") or task.get("depends_on") or []

                                    st.markdown(f"**Task {order} — {task_id}**")
                                    if description:
                                        st.write(description)
                                    else:
                                        st.write("_No description provided_")

                                    # show metadata compactly
                                    md = {
                                        "order": order,
                                        "input_data": input_data,
                                        "dependencies": dependencies
                                    }
                                    st.code(json.dumps(md, indent=2))
                                else:
                                    # primitive task representation (string, etc.)
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