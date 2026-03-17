# ai_coach/agent.py

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from db_reader import get_recent_runs, get_training_stats
from rag import search_running_docs

load_dotenv()

SYSTEM_PROMPT = """You are an expert AI running coach with deep knowledge 
of running science and training methodology.

You have access to:
1. The user's actual run history from their GPS tracking app
2. Running science documents including Jack Daniels' Running Formula

Your coaching style:
- Always base advice on the user's ACTUAL data, not generic advice
- Reference specific runs when relevant
- Be encouraging but honest
- Give specific, actionable recommendations
- Always explain WHY you're recommending something
- Cite the running science when relevant

When answering:
1. First check the user's recent runs and stats
2. Search running docs if needed for methodology
3. Combine both to give personalized advice
"""

def create_coach():
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        openai_api_key=os.environ["OPENAI_API_KEY"]
    )

    tools = [
        get_recent_runs,
        get_training_stats,
        search_running_docs
    ]

    agent = create_react_agent(
        llm,
        tools,
        prompt=SYSTEM_PROMPT
    )

    return agent


def ask_coach(agent, question: str, history: list) -> str:
    messages = history + [{"role": "user", "content": question}]

    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content