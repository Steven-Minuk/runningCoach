# ai_coach/app.py

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from agent import create_coach, ask_coach

st.set_page_config(
    page_title="AI Running Coach",
    page_icon="🏃",
    layout="centered"
)

st.title("🏃 AI Running Coach")
st.caption("Powered by your training data + running science")

# Initialize
if "agent" not in st.session_state:
    with st.spinner("Loading your coach..."):
        st.session_state.agent = create_coach()

if "history" not in st.session_state:
    st.session_state.history = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input
if question := st.chat_input("Ask your running coach..."):

    # Show user message
    with st.chat_message("user"):
        st.write(question)
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    # Get AI response
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

    # Update history for context
    st.session_state.history.append({
        "role": "user",
        "content": question
    })
    st.session_state.history.append({
        "role": "assistant",
        "content": response
    })