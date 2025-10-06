# app/supervisor.py
"""Lightweight bridge to the LangGraph agent used by the FastAPI routers."""
from __future__ import annotations
import logging
import os
from functools import lru_cache
from typing import Dict, Optional
from langchain_core.messages import HumanMessage
from core.agent import get_agent
from core.supervisor import process_message

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_cached_agent():
    """Return a singleton LangGraph agent instance.

    App Runner keeps the process warm between requests, so caching the agent
    avoids re-creating the Bedrock client and database connections on every
    request.  The cache is invalidated automatically on code reloads.
    """

    verbose = os.getenv("LLM_AGENT_VERBOSE", "0") == "1"
    if verbose:
        log.info("Creating LangGraph agent (cached instance)")
    return get_agent()


def handle_query(
    query: str,
    *,
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    lang: Optional[str] = None,
) -> Dict:
    """Execute the LangGraph agent with a single-turn conversation.

    Parameters
    ----------
    query:
        Raw user input.
    user_id / thread_id:
        Optional identifiers that allow the supervisor to reuse memory threads.
    lang:
        Kept for backwards compatibility with previous callers (the agent is
        already multilingual thanks to the prompts in :mod:`src`).
    """

    query = (query or "").strip()
    if not query:
        return {
            "ok": False,
            "type": "error",
            "error": "empty_query",
            "detail": "Query payload cannot be empty.",
        }

    agent = _get_cached_agent()
    state = {"messages": [HumanMessage(query)]}

    try:
        response, used_thread_id = process_message(
            agent,
            state,
            user_id=user_id,
            thread_id=thread_id,
            verbose=os.getenv("LLM_AGENT_VERBOSE", "0") == "1",
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        log.exception("LangGraph agent failed")
        return {
            "ok": False,
            "type": "error",
            "error": "agent_failure",
            "detail": str(exc),
        }

    return {
        "ok": True,
        "type": "llm",
        "data": response,
        "thread_id": used_thread_id,
        "language": lang or "auto",
    }


__all__ = ["handle_query"]
