from .state import MainRouterState


async def disambiguation_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("🔍 DISAMBIGUATION NODE")
    print("="*80)
    
    validation_msg = state.get("validation_message", "")
    
    formatted_message = f"""🔍 **Disambiguation Required**

{validation_msg}

Please specify which option you meant, and I'll continue with your query."""
    
    print(f"[DISAMBIGUATION] Mensaje formateado")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": formatted_message,
        "needs_user_input": True
    }


async def not_found_responder_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("❌ NOT FOUND RESPONDER")
    print("="*80)
    
    validation_msg = state.get("validation_message", "")
    question = state.get("question", "")
    
    formatted_message = f"""❌ **Entity Not Found**

I couldn't find the entity you're looking for in our database.

**Your question:** {question}

**Details:** {validation_msg}

Please check the spelling or try a different search term."""
    
    print(f"[NOT_FOUND] Mensaje formateado")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": formatted_message,
        "needs_user_input": False
    }


async def error_handler_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("⚠️ ERROR HANDLER")
    print("="*80)
    
    error = state.get("error", "Unknown error")
    question = state.get("question", "")
    
    formatted_message = f"""⚠️ **System Error**

I encountered an error while processing your question.

**Your question:** {question}

**Error:** {error}

Please try rephrasing your question or contact support if the issue persists."""
    
    print(f"[ERROR_HANDLER] Error: {error}")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": formatted_message,
        "needs_user_input": False
    }


async def responder_formatter_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("📝 RESPONDER/FORMATTER")
    print("="*80)
    
    answer = state.get("answer", "")
    
    if not answer:
        print("[FORMATTER] ⚠️ No hay respuesta para formatear")
        return {
            **state,
            "answer": "I couldn't generate a response. Please try again."
        }
    
    print(f"[FORMATTER] ✅ Respuesta formateada ({len(answer)} caracteres)")
    print("="*80 + "\n")
    
    return state
