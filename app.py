import streamlit as st
import requests
from typing import Optional, Any

st.set_page_config(page_title="Prompt Tester — n8n Decomposer", layout="centered")

def call_n8n_webhook(webhook_url: str, payload: dict, auth_header: Optional[str] = None, timeout: int = 30) -> Any:
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
    # optional override for quick testing without secrets
    webhook_url_override = st.text_input("Webhook URL (optional - overrides secret)", value="")
    auth_header_override = st.text_input("Authorization header (optional - overrides secret)", value="")
    submitted = st.form_submit_button("Run test")

def normalize_result(result):
    """
    Try to find tasks in common shapes:
      - {"output": {"tasks": [...]}}
      - {"tasks": [...]}
      - result itself is the tasks list
    Returns (tasks_list_or_None, raw_result)
    """
    if not result:
        return None, result
    if isinstance(result, dict):
        # common nested shapes
        if "output" in result and isinstance(result["output"], dict) and "tasks" in result["output"]:
            return result["output"]["tasks"], result
        if "tasks" in result:
            return result["tasks"], result
    if isinstance(result, list):
        # maybe the webhook returned tasks list directly
        return result, result
    return None, result

def render_task(task, idx):
    # robust display for the structured task object
    st.markdown(f"**Task {idx}:** `{task.get('task_id', 'unknown')}` — order: {task.get('order', 'N/A')}")
    desc = task.get("description")
    if desc:
        st.write(f"**Description:** {desc}")
    else:
        # fallback to any string-y representation
        st.write("**Description:**")
        st.write(task)
    # input_data
    input_data = task.get("input_data")
    if input_data:
        with st.expander("Input data (click to expand)"):
            st.json(input_data)
    # dependencies
    deps = task.get("dependencies")
    if deps:
        st.write(f"**Dependencies:** {deps}")
    # any extra fields
    extras = {k: v for k, v in task.items() if k not in {"task_id", "description", "order", "input_data", "dependencies"}}
    if extras:
        with st.expander("Other fields"):
            st.json(extras)

if submitted:
    if not query or not query.strip():
        st.error("Please enter a query first.")
    else:
        webhook_url = webhook_url_override.strip() or st.secrets.get("N8N_WEBHOOK_URL")
        auth_header = auth_header_override.strip() or st.secrets.get("N8N_AUTH_HEADER")  # optional
        if not webhook_url:
            st.error("Webhook URL missing — add N8N_WEBHOOK_URL in secrets or provide it above.")
        else:
            with st.spinner("Calling n8n..."):
                try:
                    payload = {"query": query}
                    result = call_n8n_webhook(webhook_url, payload, auth_header=auth_header)

                    st.subheader("Raw response")
                    # show raw JSON/text for debugging
                    try:
                        st.json(result)
                    except Exception:
                        st.write(result)

                    tasks_data, raw = normalize_result(result)

                    st.subheader("Structured Output")
                    if tasks_data and isinstance(tasks_data, list):
                        for idx, task in enumerate(tasks_data, start=1):
                            if isinstance(task, dict):
                                render_task(task, idx)
                            else:
                                # handle non-dict tasks (strings, etc.)
                                st.markdown(f"**Task {idx}:**")
                                st.write(task)
                    else:
                        st.warning("No tasks found in response. (Searched for `output.tasks`, `tasks`, or top-level list.)")
                        st.caption("If your webhook returns a different shape, paste the raw response above and I can adapt the parser.")

                    st.success("✅ Done")

                except Exception as e:
                    st.error(f"Request failed: {e}")

st.markdown("---")
st.caption("Built for quick prompt testing")