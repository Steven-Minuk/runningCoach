# ai_coach/app.py

import streamlit as st
import sys
import os
import json
import uuid
from datetime import datetime, timezone

sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from azure.storage.blob import BlobServiceClient
from agent import create_coach, ask_coach

CONVERSATIONS_CONTAINER = "conversations"


# ─────────────────────────────────────────
# Blob helpers
# ─────────────────────────────────────────

def get_blob_service() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    )


def list_sessions() -> list[dict]:
    """Return all saved sessions sorted by last modified (newest first)."""
    try:
        service = get_blob_service()
        container = service.get_container_client(CONVERSATIONS_CONTAINER)
        blobs = list(container.list_blobs())
        sessions = []
        for blob in blobs:
            session_id = blob.name.replace(".json", "")
            last_modified = blob.last_modified.strftime("%Y-%m-%d %H:%M")
            sessions.append({
                "session_id": session_id,
                "label": f"{last_modified}  —  {session_id[:8]}...",
                "last_modified": blob.last_modified,
            })
        sessions.sort(key=lambda x: x["last_modified"], reverse=True)
        return sessions
    except Exception:
        return []


def load_conversation(session_id: str) -> list[dict]:
    """Load conversation history from blob. Returns empty list if not found."""
    try:
        service = get_blob_service()
        blob_client = service.get_blob_client(
            container=CONVERSATIONS_CONTAINER,
            blob=f"{session_id}.json"
        )
        data = blob_client.download_blob().readall()
        return json.loads(data)
    except Exception:
        return []


def save_conversation(session_id: str, messages: list[dict]) -> None:
    """Overwrite the session blob with the current message list."""
    try:
        service = get_blob_service()
        blob_client = service.get_blob_client(
            container=CONVERSATIONS_CONTAINER,
            blob=f"{session_id}.json"
        )
        blob_client.upload_blob(
            json.dumps(messages, indent=2, ensure_ascii=False),
            overwrite=True
        )
    except Exception as e:
        st.warning(f"Could not save conversation: {e}")


def new_session_id() -> str:
    """Generate a session ID based on current timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")


# ─────────────────────────────────────────
# Page config
# ─────────────────────────────────────────

st.set_page_config(
    page_title="AI Running Coach",
    page_icon="🏃",
    layout="centered"
)

st.title("🏃 AI Running Coach")
st.caption("Powered by your training data + running science")


# ─────────────────────────────────────────
# Sidebar — session management
# ─────────────────────────────────────────

with st.sidebar:
    st.header("Sessions")

    if st.button("New session", use_container_width=True):
        st.session_state.session_id = new_session_id()
        st.session_state.messages  = []
        st.session_state.history   = []
        st.rerun()

    st.divider()

    sessions = list_sessions()
    if sessions:
        st.subheader("Past sessions")
        for s in sessions:
            if st.button(s["label"], key=s["session_id"], use_container_width=True):
                st.session_state.session_id = s["session_id"]
                loaded = load_conversation(s["session_id"])
                st.session_state.messages = loaded
                st.session_state.history  = loaded
                st.rerun()
    else:
        st.info("No past sessions yet.")

    st.divider()
    if "session_id" in st.session_state:
        st.caption(f"Current session:\n`{st.session_state.session_id}`")


# ─────────────────────────────────────────
# Initialize state
# ─────────────────────────────────────────

if "agent" not in st.session_state:
    with st.spinner("Loading your coach..."):
        st.session_state.agent = create_coach()

if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "history" not in st.session_state:
    st.session_state.history = []


# ─────────────────────────────────────────
# Chat UI
# ─────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if question := st.chat_input("Ask your running coach..."):

    with st.chat_message("user"):
        st.write(question)
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = ask_coach(
                st.session_state.agent,
                question,
                st.session_state.history
            )
        st.write(response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    st.session_state.history = st.session_state.messages.copy()

    # Save full conversation to blob after every turn
    save_conversation(
        st.session_state.session_id,
        st.session_state.messages
    )