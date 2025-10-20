from typing import List
from .state import MainRouterState
from src.strands.utils.validators_shared import resolve_country_iso, resolve_platform_name

ESSENTIAL_PARAMS = {
    "platform": {
        "params": ["platform_name"],
        "defaults": {},
        "question_keywords": ["netflix", "disney", "hbo", "amazon", "prime", "apple tv", "paramount"]
    },
    "business": {
        "params": ["country"],
        "defaults": {
            "time_window": "last_month"
        },
        "question_keywords": ["revenue", "subscribers", "growth", "market", "exclusive", "exclusivity", "catalog", "similarity", "comparison"]
    },
    "content": {
        "params": ["content_type", "platform"],
        "defaults": {
            "content_type": "movie"
        },
        "question_keywords": ["movie", "series", "film", "show", "episode"]
    },
    "talent": {
        "params": ["person_name"],
        "defaults": {},
        "question_keywords": ["director", "actor", "actress", "creator", "writer"]
    }
}


def detect_missing_params(question: str, domain: str) -> List[str]:
    if domain not in ESSENTIAL_PARAMS:
        return []
    
    config = ESSENTIAL_PARAMS[domain]
    question_lower = question.lower()
    missing = []
    
    for param in config["params"]:
        default = config["defaults"].get(param)
        
        if default is not None:
            continue
        
        if param == "platform_name":
            # Use the robust resolve_platform_name function to detect if a platform is mentioned
            words = question.split()
            platform_found = False
            
            # Try single words
            for word in words:
                if resolve_platform_name(word):
                    platform_found = True
                    break
            
            # Try two-word combinations (e.g., "Disney Plus", "Amazon Prime")
            if not platform_found:
                for i in range(len(words) - 1):
                    two_word = f"{words[i]} {words[i+1]}"
                    if resolve_platform_name(two_word):
                        platform_found = True
                        break
            
            if not platform_found:
                missing.append(param)
        
        elif param == "country":
            # Use the robust resolve_country_iso function to detect if a country is mentioned
            # Try to extract potential country mentions from the question
            words = question.split()
            country_found = False
            
            # Try single words
            for word in words:
                if resolve_country_iso(word):
                    country_found = True
                    break
            
            # Try two-word combinations (e.g., "Estados Unidos", "United States")
            if not country_found:
                for i in range(len(words) - 1):
                    two_word = f"{words[i]} {words[i+1]}"
                    if resolve_country_iso(two_word):
                        country_found = True
                        break
            
            # Try three-word combinations (e.g., "United States of America")
            if not country_found:
                for i in range(len(words) - 2):
                    three_word = f"{words[i]} {words[i+1]} {words[i+2]}"
                    if resolve_country_iso(three_word):
                        country_found = True
                        break
            
            if not country_found:
                missing.append(param)
        
        elif param == "person_name":
            if any(kw in question_lower for kw in ["director", "actor", "creator"]):
                words = question.split()
                has_proper_name = any(w[0].isupper() and len(w) > 2 for w in words if w.isalpha())
                if not has_proper_name:
                    missing.append(param)
        
        elif param == "content_type":
            if not any(kw in question_lower for kw in ["movie", "series", "film", "show", "episode"]):
                missing.append(param)
    
    return missing


def should_request_clarification(state: MainRouterState) -> bool:
    question = state.get("question", "")
    selected_graph = state.get("selected_graph", "")
    confidence = state.get("routing_confidence", 1.0)
    
    if confidence < 0.3:
        return False
    
    missing = detect_missing_params(question, selected_graph)
    return len(missing) == 1


def generate_clarification_message(state: MainRouterState) -> str:
    question = state.get("question", "")
    selected_graph = state.get("selected_graph", "")
    missing = detect_missing_params(question, selected_graph)
    
    if not missing:
        return "Could you please provide more details?"
    
    param = missing[0]
    
    if param == "platform_name":
        return (
            f"Which streaming platform?\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Please specify the platform (e.g., Netflix, Disney+, HBO Max, Amazon Prime, etc.)"
        )
    
    elif param == "country":
        return (
            f"Which country or region?\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Please specify the country or region (e.g., Argentina, USA, Brazil, Spain, etc.)"
        )
    
    elif param == "person_name":
        return (
            f"Which person are you asking about?\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Please provide the name of the director, actor, or creator."
        )
    
    elif param == "time_window":
        return (
            f"What time period?\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Please specify the time window (e.g., last month, Q1 2024, 2023, etc.)"
        )
    
    elif param == "content_type":
        return (
            f"Movies or series?\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Please specify if you're asking about movies or TV series."
        )
    
    else:
        return (
            f"Missing information: {param}\n\n"
            f"Your question: \"{question}\"\n\n"
            f"Please provide the {param.replace('_', ' ')}."
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
        # Check if this is a re-routing failure
        if error and "No alternative graphs available" in error:
            visited_graphs = state.get("visited_graphs", [])
            clarification_msg = (
                f"I'm unable to answer this question with the available tools.\n\n"
                f"Your question: \"{question}\"\n\n"
                f"I've tried analyzing it from different perspectives ({', '.join(visited_graphs)}) "
                f"but couldn't find the right approach. This might be because:\n"
                f"• The question requires data I don't have access to\n"
                f"• The question is outside my domain of expertise\n"
                f"• The question needs to be more specific\n\n"
                f"Could you please rephrase your question or ask something else?"
            )
            print("[CLARIFIER] Re-routing failure, providing helpful message")
        elif missing:
            clarification_msg = generate_clarification_message(state)
            print(f"[CLARIFIER] Requesting: {missing[0]}")
        else:
            confidence = state.get("routing_confidence", 0.0)
            clarification_msg = (
                f"Low Confidence ({confidence:.2f})\n\n"
                f"I need more information to answer your question:\n"
                f"\"{question}\"\n\n"
                f"Could you please rephrase or provide more details?"
            )
            print("[CLARIFIER] Low confidence fallback")
    
    print(f"[CLARIFIER] Message preview: {clarification_msg[:100]}...")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": clarification_msg,
        "needs_user_input": True,
        "missing_params": missing
    }