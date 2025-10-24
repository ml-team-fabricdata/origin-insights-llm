from typing import List
from .state import MainRouterState
from .prompts import CLARIFICATION_PROMPT
from app.strands.infrastructure.validators.shared import resolve_country_iso, resolve_platform_name
from strands import Agent
from app.strands.config.llm_models import MODEL_CLASSIFIER

ESSENTIAL_PARAMS = {
    "platform": {
        "params": ["platform_name"],
        "defaults": {},
        "question_keywords": ["netflix", "disney", "hbo", "amazon", "prime", "apple tv", "paramount"]
    },
    "business": {
        "params": ["country"],
        "defaults": {"time_window": "last_month"},
        "question_keywords": ["revenue", "subscribers", "growth", "market", "exclusive", 
                             "exclusivity", "catalog", "similarity", "comparison"]
    },
    "content": {
        "params": ["content_type", "platform"],
        "defaults": {"content_type": "movie"},
        "question_keywords": ["movie", "series", "film", "show", "episode"]
    },
    "talent": {
        "params": ["person_name"],
        "defaults": {},
        "question_keywords": ["director", "actor", "actress", "creator", "writer"]
    }
}


def _check_platform_in_question(question: str) -> bool:
    words = question.split()
    
    for word in words:
        if resolve_platform_name(word):
            return True
    
    for i in range(len(words) - 1):
        if resolve_platform_name(f"{words[i]} {words[i+1]}"):
            return True
    
    return False


def _check_country_in_question(question: str) -> bool:
    words = question.split()
    
    for word in words:
        if resolve_country_iso(word):
            return True
    
    for i in range(len(words) - 1):
        if resolve_country_iso(f"{words[i]} {words[i+1]}"):
            return True
    
    if len(words) > 2:
        for i in range(len(words) - 2):
            if resolve_country_iso(f"{words[i]} {words[i+1]} {words[i+2]}"):
                return True
    
    return False


def _check_person_name_in_question(question: str, question_lower: str) -> bool:
    if not any(kw in question_lower for kw in ["director", "actor", "creator"]):
        return True
    
    words = question.split()
    return any(w[0].isupper() and len(w) > 2 for w in words if w.isalpha())


def _check_content_type_in_question(question_lower: str) -> bool:
    return any(kw in question_lower for kw in ["movie", "series", "film", "show", "episode"])


def detect_missing_params(question: str, domain: str) -> List[str]:
    if domain not in ESSENTIAL_PARAMS:
        return []
    
    config = ESSENTIAL_PARAMS[domain]
    question_lower = question.lower()
    missing = []
    
    for param in config["params"]:
        if config["defaults"].get(param) is not None:
            continue
        
        param_checks = {
            "platform_name": lambda: not _check_platform_in_question(question),
            "country": lambda: not _check_country_in_question(question),
            "person_name": lambda: not _check_person_name_in_question(question, question_lower),
            "content_type": lambda: not _check_content_type_in_question(question_lower)
        }
        
        check_fn = param_checks.get(param)
        if check_fn and check_fn():
            missing.append(param)
    
    return missing


def should_request_clarification(state: MainRouterState) -> bool:
    confidence = state.get("routing_confidence", 1.0)
    if confidence < 0.3:
        return False
    
    question = state.get("question", "")
    selected_graph = state.get("selected_graph", "")
    missing = detect_missing_params(question, selected_graph)
    
    return len(missing) == 1


async def _generate_clarification_for_param(param: str, question: str) -> str:
    """Generate natural clarification message using LLM."""
    param_names = {
        "platform_name": "streaming platform",
        "country": "country or region",
        "person_name": "person's name",
        "time_window": "time period",
        "content_type": "content type (movie or series)"
    }
    
    param_name = param_names.get(param, param.replace('_', ' '))
    
    agent = Agent(model=MODEL_CLASSIFIER, system_prompt=CLARIFICATION_PROMPT)
    response = await agent.invoke_async(
        f"Question: {question}\nMissing: {param_name}"
    )
    
    if hasattr(response, 'message'):
        message = response.message
        if isinstance(message, dict) and 'content' in message:
            return message['content'][0]['text']
        elif isinstance(message, str):
            return message
    
    return str(response)


async def generate_clarification_message(state: MainRouterState) -> str:
    question = state.get("question", "")
    selected_graph = state.get("selected_graph", "")
    missing = detect_missing_params(question, selected_graph)
    
    if not missing:
        return "Could you please provide more details?"
    
    return await _generate_clarification_for_param(missing[0], question)


def _generate_rerouting_failure_message(state: MainRouterState) -> str:
    question = state.get("question", "")
    visited_graphs = state.get("visited_graphs", [])
    
    return (
        f"I'm unable to answer this question with the available tools.\n\n"
        f"Your question: \"{question}\"\n\n"
        f"I've tried analyzing it from different perspectives ({', '.join(visited_graphs)}) "
        f"but couldn't find the right approach. This might be because:\n"
        f"• The question requires data I don't have access to\n"
        f"• The question is outside my domain of expertise\n"
        f"• The question needs to be more specific\n\n"
        f"Could you please rephrase your question or ask something else?"
    )


def _generate_low_confidence_message(state: MainRouterState) -> str:
    question = state.get("question", "")
    confidence = state.get("routing_confidence", 0.0)
    
    return (
        f"Low Confidence ({confidence:.2f})\n\n"
        f"I need more information to answer your question:\n"
        f"\"{question}\"\n\n"
        f"Could you please rephrase or provide more details?"
    )


async def clarifier_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("CLARIFIER - Smart Parameter Detection")
    print("="*80)
    
    question = state.get("question", "")
    selected_graph = state.get("selected_graph", "")
    error = state.get("error", "")
    
    missing = detect_missing_params(question, selected_graph)
    
    print(f"[CLARIFIER] Domain: {selected_graph}")
    print(f"[CLARIFIER] Missing params: {missing if missing else 'None'}")
    if error:
        print(f"[CLARIFIER] Error: {error}")
    
    clarification_msg = state.get("clarification_message")
    
    if not clarification_msg:
        if error and "No alternative graphs available" in error:
            clarification_msg = _generate_rerouting_failure_message(state)
            print("[CLARIFIER] Re-routing failure, providing helpful message")
        elif missing:
            clarification_msg = await generate_clarification_message(state)
            print(f"[CLARIFIER] Requesting: {missing[0]}")
        else:
            clarification_msg = _generate_low_confidence_message(state)
            print("[CLARIFIER] Low confidence fallback")
    
    print(f"[CLARIFIER] Message preview: {clarification_msg[:100]}...")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": clarification_msg,
        "needs_user_input": True,
        "missing_params": missing
    }
