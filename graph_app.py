# graph_app.py
from typing import TypedDict, Literal, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from strands import Agent
from src.prompt_templates.prompt import response_prompt, prompt as SYSTEM_PROMPT

# Importar todas las tools individuales
from agent_strands import (
    # Pricing tools
    prices_latest, prices_history, prices_changes_last_n_days, prices_stats, hits_with_quality,
    # Intelligence tools
    get_platform_exclusivity_by_country, catalog_similarity_for_platform, titles_in_A_not_in_B
)

class State(TypedDict, total=False):
    question: str
    answer: str
    raw_data: List[Dict[str, Any]]  # Datos crudos de las tools
    task: Literal["pricing", "intelligence"]
    tool_calls_count: int  # Contador de llamadas a tools
    max_iterations: int  # Máximo de iteraciones permitidas 

# --- NODOS INDIVIDUALES PARA CADA TOOL ---
# Cada nodo ejecuta un agente con UNA SOLA tool específica

# Pricing Tools Nodes
async def node_prices_latest(state: State) -> State:
    """Ejecuta solo la tool prices_latest."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_latest],  # Solo esta tool
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "pricing", "tool_calls_count": count}

async def node_prices_history(state: State) -> State:
    """Ejecuta solo la tool prices_history."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_history],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "pricing", "tool_calls_count": count}

async def node_prices_changes(state: State) -> State:
    """Ejecuta solo la tool prices_changes_last_n_days."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_changes_last_n_days],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "pricing", "tool_calls_count": count}

async def node_prices_stats(state: State) -> State:
    """Ejecuta solo la tool prices_stats."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_stats],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "pricing", "tool_calls_count": count}

async def node_hits_quality(state: State) -> State:
    """Ejecuta solo la tool hits_with_quality."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[hits_with_quality],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "pricing", "tool_calls_count": count}

# Intelligence Tools Nodes
async def node_platform_exclusivity(state: State) -> State:
    """Ejecuta solo la tool get_platform_exclusivity_by_country."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[get_platform_exclusivity_by_country],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "intelligence", "tool_calls_count": count}

async def node_catalog_similarity(state: State) -> State:
    """Ejecuta solo la tool catalog_similarity_for_platform."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[catalog_similarity_for_platform],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "intelligence", "tool_calls_count": count}

async def node_titles_diff(state: State) -> State:
    """Ejecuta solo la tool titles_in_A_not_in_B."""
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[titles_in_A_not_in_B],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    return {**state, "answer": answer, "task": "intelligence", "tool_calls_count": count}

# Nodos supervisores que deciden si continuar o terminar
async def pricing_supervisor(state: State) -> State:
    """Supervisor que decide si necesita más tools de pricing o si termina."""
    return state

async def intelligence_supervisor(state: State) -> State:
    """Supervisor que decide si necesita más tools de intelligence o si termina."""
    return state

async def main_supervisor(state: State) -> State:
    """Supervisor principal que coordina entre pricing e intelligence."""
    return state

def should_continue_pricing(state: State) -> str:
    """Decide si el pricing supervisor necesita más tools de pricing o vuelve al main."""
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 3)
    
    # Si ya alcanzó el máximo de iteraciones, ir al supervisor principal
    if count >= max_iter:
        return "main_supervisor"
    
    # Si tiene respuesta significativa, ir al supervisor principal
    answer = state.get("answer", "")
    if answer and len(str(answer)) > 50:
        return "main_supervisor"
    
    # Si no tiene respuesta o es muy corta, volver al router para otra tool de pricing
    return "router_pricing"

def should_continue_intelligence(state: State) -> str:
    """Decide si el intelligence supervisor necesita más tools o vuelve al main."""
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 3)
    
    # Si ya alcanzó el máximo de iteraciones, ir al supervisor principal
    if count >= max_iter:
        return "main_supervisor"
    
    # Si tiene respuesta significativa, ir al supervisor principal
    answer = state.get("answer", "")
    if answer and len(str(answer)) > 50:
        return "main_supervisor"
    
    # Si no tiene respuesta o es muy corta, volver al router para otra tool de intelligence
    return "router_intelligence"

def should_continue_main(state: State) -> str:
    """Supervisor principal decide si necesita más información o termina."""
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 3)
    answer = state.get("answer", "")
    
    # Si alcanzó el máximo de iteraciones, terminar
    if count >= max_iter:
        return "format_response"
    
    # Si no hay respuesta o es insuficiente, preguntar al LLM qué hacer
    if not answer or len(str(answer)) < 50:
        return "format_response"
    
    # Usar LLM para decidir si necesita más información
    from langchain_aws import ChatBedrock
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    decision_prompt = f"""Analiza si la respuesta actual es suficiente para responder la pregunta del usuario.

PREGUNTA: {state.get('question', '')}
RESPUESTA ACTUAL: {answer}
TOOLS EJECUTADAS: {count}

¿La respuesta actual es suficiente y completa? Responde SOLO con:
- "SUFICIENTE" si la respuesta responde completamente la pregunta
- "NECESITA_PRICING" si necesita información adicional de precios
- "NECESITA_INTELLIGENCE" si necesita información adicional de catálogo/inteligencia
"""
    
    response = llm.invoke(decision_prompt)
    decision = response.content.strip().upper()
    
    if "NECESITA_PRICING" in decision:
        return "router_pricing"
    elif "NECESITA_INTELLIGENCE" in decision:
        return "router_intelligence"
    else:
        return "format_response"

async def format_response(state: State) -> State:
    """Nodo final que formatea la respuesta según response_prompt."""
    raw_answer = state.get("answer", "")
    question = state.get("question", "")
    
    # Crear agente de formateo sin tools
    formatter = Agent(
        model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",  # Modelo más potente para formateo
        tools=[],
        system_prompt=response_prompt
    )
    
    # Formatear la respuesta
    formatted = await formatter.invoke_async(
        f"Question: {question}\n\nRaw data collected:\n{raw_answer}\n\nFormat this response following the rules."
    )
    
    final_answer = getattr(formatted, "message", str(formatted))
    return {"question": question, "answer": final_answer, "task": state.get("task")}

# --- Routers ---
def route_main(state: State) -> str:
    """Router principal: decide entre pricing o intelligence."""
    task = state.get("task")
    if task in ("pricing", "intelligence"):
        return task
    q = (state.get("question") or "").lower()
    pricing_kw = ["precio", "precios", "rent", "buy", "alquiler", "venta", "price", "cambios", "histórico", "stats"]
    if any(k in q for k in pricing_kw):
        return "pricing"
    return "intelligence"

def route_pricing_tool(state: State) -> str:
    """Router inteligente que usa LLM para decidir qué tool de pricing ejecutar."""
    q = state.get("question", "")
    
    router_prompt = """Eres un router inteligente. Analiza la pregunta del usuario y decide cuál es la MEJOR tool para responderla.

TOOLS DISPONIBLES:

1. **prices_latest**: Obtiene los últimos precios actuales de títulos según filtros (uid, país, plataforma, tipo de precio, definición, licencia, moneda, rango de precios). Usa esta cuando pregunten por precios actuales, últimos precios, o precios de un título/plataforma específica.

2. **prices_history**: Obtiene el histórico completo de precios de un título o conjunto de títulos a lo largo del tiempo. Usa esta cuando pregunten por evolución de precios, cambios históricos, o cómo ha variado el precio.

3. **prices_changes**: Obtiene cambios de precio en los últimos N días (subas/bajas). Usa esta cuando pregunten específicamente por cambios recientes, subas, bajas, o variaciones en un período corto.

4. **prices_stats**: Obtiene estadísticas agregadas (min, max, promedio, percentiles) de precios según filtros. Usa esta cuando pregunten por estadísticas, promedios, rangos de precios, o análisis agregado.

5. **hits_quality**: Obtiene datos de popularidad/hits con filtros de calidad (definición, licencia). Usa esta cuando pregunten por popularidad, títulos más vistos, o hits con filtros de calidad.

PREGUNTA DEL USUARIO: {question}

Responde SOLO con el nombre de la tool más apropiada (prices_latest, prices_history, prices_changes, prices_stats, o hits_quality). Sin explicaciones."""
    
    from langchain_aws import ChatBedrock
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    response = llm.invoke(router_prompt.format(question=q))
    tool_choice = response.content.strip().lower()
    
    # Mapear la respuesta a los nombres de nodos
    if "prices_changes" in tool_choice or "changes" in tool_choice:
        return "prices_changes"
    elif "prices_history" in tool_choice or "history" in tool_choice:
        return "prices_history"
    elif "prices_stats" in tool_choice or "stats" in tool_choice:
        return "prices_stats"
    elif "hits_quality" in tool_choice or "hits" in tool_choice or "quality" in tool_choice:
        return "hits_quality"
    else:
        return "prices_latest"

def route_intelligence_tool(state: State) -> str:
    """Router inteligente que usa LLM para decidir qué tool de intelligence ejecutar."""
    q = state.get("question", "")
    
    router_prompt = """Eres un router inteligente. Analiza la pregunta del usuario y decide cuál es la MEJOR tool para responderla.

TOOLS DISPONIBLES:

1. **platform_exclusivity**: Obtiene títulos exclusivos de una plataforma en un país específico. Usa esta cuando pregunten por contenido exclusivo, títulos que solo están en una plataforma, o qué tiene una plataforma que otras no tienen.

2. **catalog_similarity**: Compara la similitud del catálogo de una plataforma entre dos países. Calcula porcentaje de similitud, títulos compartidos y únicos. Usa esta cuando pregunten por comparar catálogos entre países, similitud de contenido, o diferencias regionales de una misma plataforma.

3. **titles_diff**: Obtiene títulos que están en país A pero NO en país B para una plataforma. Usa esta cuando pregunten específicamente por títulos únicos de un país vs otro, diferencias de catálogo, o qué tiene un país que otro no tiene.

PREGUNTA DEL USUARIO: {question}

Responde SOLO con el nombre de la tool más apropiada (platform_exclusivity, catalog_similarity, o titles_diff). Sin explicaciones."""
    
    from langchain_aws import ChatBedrock
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    response = llm.invoke(router_prompt.format(question=q))
    tool_choice = response.content.strip().lower()
    
    # Mapear la respuesta a los nombres de nodos
    if "catalog_similarity" in tool_choice or "similarity" in tool_choice:
        return "catalog_similarity"
    elif "titles_diff" in tool_choice or "diff" in tool_choice or "not in" in tool_choice:
        return "titles_diff"
    else:
        return "platform_exclusivity"

# --- Grafo con estructura jerárquica y loops de feedback ---
graph = StateGraph(State)

# Agregar nodos individuales de pricing tools
graph.add_node("prices_latest", node_prices_latest)
graph.add_node("prices_history", node_prices_history)
graph.add_node("prices_changes", node_prices_changes)
graph.add_node("prices_stats", node_prices_stats)
graph.add_node("hits_quality", node_hits_quality)

# Agregar nodos individuales de intelligence tools
graph.add_node("platform_exclusivity", node_platform_exclusivity)
graph.add_node("catalog_similarity", node_catalog_similarity)
graph.add_node("titles_diff", node_titles_diff)

# Agregar nodos de routing y supervisión
graph.add_node("router_main", lambda s: s)
graph.add_node("router_pricing", lambda s: s)
graph.add_node("router_intelligence", lambda s: s)
graph.add_node("pricing_supervisor", pricing_supervisor)
graph.add_node("intelligence_supervisor", intelligence_supervisor)
graph.add_node("main_supervisor", main_supervisor)

# Agregar nodo de formateo
graph.add_node("format_response", format_response)

# Flujo del grafo con loops de feedback jerárquicos:
# START -> router_main -> (router_pricing | router_intelligence) 
#   -> tool -> supervisor_específico -> main_supervisor 
#   -> (volver a router_pricing | router_intelligence | format_response) -> END

# Router principal (primera vez)
graph.add_edge(START, "router_main")
graph.add_conditional_edges(
    "router_main",
    route_main,
    {"pricing": "router_pricing", "intelligence": "router_intelligence"}
)

# Router de pricing -> decide qué tool ejecutar
graph.add_conditional_edges(
    "router_pricing",
    route_pricing_tool,
    {
        "prices_latest": "prices_latest",
        "prices_history": "prices_history",
        "prices_changes": "prices_changes",
        "prices_stats": "prices_stats",
        "hits_quality": "hits_quality"
    }
)

# Router de intelligence -> decide qué tool ejecutar
graph.add_conditional_edges(
    "router_intelligence",
    route_intelligence_tool,
    {
        "platform_exclusivity": "platform_exclusivity",
        "catalog_similarity": "catalog_similarity",
        "titles_diff": "titles_diff"
    }
)

# Todas las pricing tools -> pricing_supervisor
graph.add_edge("prices_latest", "pricing_supervisor")
graph.add_edge("prices_history", "pricing_supervisor")
graph.add_edge("prices_changes", "pricing_supervisor")
graph.add_edge("prices_stats", "pricing_supervisor")
graph.add_edge("hits_quality", "pricing_supervisor")

# Todas las intelligence tools -> intelligence_supervisor
graph.add_edge("platform_exclusivity", "intelligence_supervisor")
graph.add_edge("catalog_similarity", "intelligence_supervisor")
graph.add_edge("titles_diff", "intelligence_supervisor")

# Supervisores específicos deciden si continuar en su categoría o ir al main
graph.add_conditional_edges(
    "pricing_supervisor",
    should_continue_pricing,
    {"router_pricing": "router_pricing", "main_supervisor": "main_supervisor"}
)

graph.add_conditional_edges(
    "intelligence_supervisor",
    should_continue_intelligence,
    {"router_intelligence": "router_intelligence", "main_supervisor": "main_supervisor"}
)

# Main supervisor decide si necesita otra categoría o termina
graph.add_conditional_edges(
    "main_supervisor",
    should_continue_main,
    {
        "router_pricing": "router_pricing",
        "router_intelligence": "router_intelligence",
        "format_response": "format_response"
    }
)

# format_response -> END
graph.add_edge("format_response", END)

app = graph.compile()

import asyncio
import time

if __name__ == "__main__":
    # Imprimir estructura del grafo
    print("\n" + "="*60)
    print("📊 ESTRUCTURA DEL GRAFO")
    print("="*60)
    
    # Imprimir resumen del grafo
    print("""
    Flujo Principal:
    ================
    START → router_main → [pricing | intelligence]
    
    Pricing Branch:
    ---------------
    router_pricing → tool → pricing_supervisor → main_supervisor
    
    Intelligence Branch:
    --------------------
    router_intelligence → tool → intelligence_supervisor → main_supervisor
    
    Main Supervisor:
    ----------------
    main_supervisor → [router_pricing | router_intelligence | format_response]
    
    End:
    ----
    format_response → END
    
    Tools Disponibles:
    - Pricing: prices_latest, prices_history, prices_changes, prices_stats, hits_quality
    - Intelligence: platform_exclusivity, catalog_similarity, titles_diff
    """)
    print("="*60 + "\n")
    
    # Intentar guardar diagrama (opcional)
    try:
        from langgraph.graph import MermaidDrawMethod
        png_data = app.get_graph().draw_mermaid_png(

        )
        with open("graph_structure.png", "wb") as f:
            f.write(png_data)
        print("✅ Diagrama PNG guardado en: graph_structure.png\n")
    except Exception as e:
        print(f"ℹ️  Diagrama PNG no disponible (grafo muy complejo)\n")
    async def ask(q: str, task: str | None = None, max_iterations: int = 3):
        payload = {
            "question": q,
            "tool_calls_count": 0,
            "max_iterations": max_iterations
        }
        if task:
            payload["task"] = task
        
        start_time = time.time()
        result = await app.ainvoke(payload, config={}, context={})
        elapsed_time = time.time() - start_time
        
        print(f"\n🔍 Pregunta: {q}")
        print(f"⏱️  Tiempo de respuesta: {elapsed_time:.2f}s")
        print(f"🔧 Tools ejecutadas: {result.get('tool_calls_count', 0)}")
        print(f"📋 Respuesta:\n{result.get('answer', 'No answer')}\n")
        return result
    
    async def main():
        await ask("Que plataforma tiene más contenido disponible en US.")
        await ask("Que peliculas tiene Netflix en US que no tiene Amazon Prime.")
    asyncio.run(main())