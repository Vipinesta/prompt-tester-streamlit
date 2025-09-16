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

# --- Styling: subtle card-like UI for tasks ---
st.markdown(
    """
    <style>
    /* Card around each task expander */
    .stExpander > div[data-testid="stExpander"] {
        border-radius: 10px;
        padding: 0.25rem 0.5rem;
        box-shadow: 0 6px 18px rgba(0,0,0,0.18);
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00));
    }
    /* Improve JSON/code block padding */
    .stCodeBlock, pre {
        border-radius: 8px;
        padding: 0.75rem;
        background-color: rgba(0,0,0,0.45) !important;
        color: #d6f8ff !important;
        overflow-x: auto;
    }
    /* Smaller metadata text */
    .task-meta {
        font-size: 0.92rem;
        color: #bfc7cd;
    }
    /* Headline spacing */
    .structured-output {
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚡ Prompt Testing Playground")
st.write("Enter a query and hit **Run test** — output now presented in an improved UI.")

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
                    st.markdown('<div class="structured-output"></div>', unsafe_allow_html=True)

                    try:
                        # Extract tasks from possible locations
                        tasks_raw = None
                        if isinstance(result, dict):
                            tasks_raw = result.get("output", {}).get("tasks")
                            if tasks_raw is None:
                                tasks_raw = result.get("tasks")
                        else:
                            tasks_raw = None

                        if tasks_raw and isinstance(tasks_raw, list):
                            for idx, task in enumerate(tasks_raw, start=1):
                                if isinstance(task, dict):
                                    # Normalization for both legacy and new keys
                                    task_id = task.get("task_id") or task.get("id") or f"t{idx}"
                                    description = task.get("description") or task.get("title") or (
                                        (list(task.values())[0] if len(task) == 1 else None)
                                    )
                                    order = task.get("order") or task.get("position") or idx
                                    input_data = task.get("input_data") or task.get("params") or {}
                                    dependencies = task.get("dependencies") or task.get("depends_on") or []

                                    # Nice expander per task
                                    expander_title = f"Task {order} — {task_id}"
                                    with st.expander(expander_title, expanded=True):
                                        # Description / title
                                        if description:
                                            st.write(description)
                                        else:
                                            st.write("_No description provided_")

                                        # Two-column metadata + payload
                                        left, right = st.columns([2, 1])
                                        with left:
                                            st.subheader("Input Data")
                                            # st.json shows nice formatted JSON with interactive folding
                                            if input_data:
                                                st.json(input_data)
                                            else:
                                                st.info("No input parameters.")

                                        with right:
                                            st.subheader("Metadata")
                                            st.markdown(f"<div class='task-meta'><strong>Order:</strong> {order}</div>", unsafe_allow_html=True)
                                            # Dependencies
                                            st.markdown("<div class='task-meta'><strong>Dependencies:</strong></div>", unsafe_allow_html=True)
                                            if dependencies:
                                                for dep in dependencies:
                                                    st.markdown(f"- `{dep}`")
                                            else:
                                                st.markdown("_None_")

                                        # Compact raw view for debugging if needed
                                        with st.expander("Show raw task JSON", expanded=False):
                                            st.code(json.dumps(task, indent=2))

                                        st.markdown("---")
                                else:
                                    # primitive task representation
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
