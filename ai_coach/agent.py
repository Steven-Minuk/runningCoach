# ai_coach/agent.py

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from db_reader import (
    get_recent_runs,
    get_training_stats,
    get_run_pace_profile,
    get_elevation_profile,
    get_best_efforts,
)
from rag import search_running_docs

load_dotenv()

SYSTEM_PROMPT = """You are an expert AI running coach with deep knowledge
of running science and training methodology.

You have access to:
1. The user's actual run history from their GPS tracking app
2. Per-kilometre pace and elevation data from every run
3. Running science documents including Jack Daniels' Running Formula

Your coaching style:
- Always base advice on the user's ACTUAL data, not generic advice
- Reference specific runs when relevant
- Be encouraging but honest
- Give specific, actionable recommendations
- Always explain WHY you're recommending something
- Cite the running science when relevant

Available tools and when to use them:
- get_recent_runs        → overview of recent training, dates, distances
- get_training_stats     → fitness level, weekly mileage trends
- get_run_pace_profile   → pacing strategy for a specific run (positive/negative splits)
- get_elevation_profile  → elevation and grade data for a specific run
- get_best_efforts       → PRs and race-distance benchmarks across all runs
- search_running_docs    → training methodology, recovery, pacing science

When answering:
1. For general training questions: check recent runs + stats first
2. For pacing or effort questions: use get_run_pace_profile on the relevant run(s)
3. For hilly course questions: use get_elevation_profile
4. For race readiness or PR questions: use get_best_efforts
5. Search running docs when methodology or science context would help
6. Combine data + science to give personalised advice
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
        get_run_pace_profile,      # new — silver
        get_elevation_profile,     # new — silver
        get_best_efforts,          # new — silver
        search_running_docs,
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