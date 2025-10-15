from .state import MainRouterState


async def clarifier_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("🤔 CLARIFIER NODE")
    print("="*80)
    
    clarification_msg = state.get("clarification_message")
    
    if not clarification_msg:
        confidence = state.get("routing_confidence", 0.0)
        candidates = state.get("routing_candidates", [])
        
        if confidence < 0.5:
            clarification_msg = (
                f"⚠️ Low Confidence ({confidence:.2f})\n\n"
                f"I'm not confident about how to handle your question:\n"
                f"'{state['question']}'\n\n"
                f"Could you please rephrase or provide more details?"
            )
        elif candidates:
            options = "\n".join([f"  - {graph} ({conf:.2f})" for graph, conf in candidates[:3]])
            clarification_msg = (
                f"🤔 Multiple Interpretations\n\n"
                f"Your question could be handled by:\n{options}\n\n"
                f"Could you please clarify which aspect you're interested in?"
            )
        else:
            clarification_msg = (
                f"❓ Clarification Needed\n\n"
                f"I need more information to answer your question:\n"
                f"'{state['question']}'\n\n"
                f"Could you please provide more details?"
            )
    
    print(f"[CLARIFIER] Mensaje: {clarification_msg[:200]}...")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": clarification_msg,
        "needs_user_input": True
    }
