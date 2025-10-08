# -*- coding: utf-8 -*-

import asyncio
import time
from typing import TypedDict, Literal, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from strands import Agent
from langchain_aws import ChatBedrock
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
    raw_data: List[Dict[str, Any]]
    task: Literal["pricing", "intelligence"]
    tool_calls_count: int
    max_iterations: int
    accumulated_data: str  # Acumular información de múltiples tools
    supervisor_decision: str  # Decisión del main supervisor
    needs_more: bool  # Flag para pricing/intelligence supervisors

# ========== NODOS INDIVIDUALES PARA CADA TOOL ==========

# Pricing Tools Nodes


async def node_prices_latest(state: State) -> State:
    """Ejecuta solo la tool prices_latest."""
    print("[TOOL] Ejecutando: prices_latest")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_latest],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] prices_latest completada (tool #{count})")

    # Acumular datos
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- prices_latest ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "pricing",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }


async def node_prices_history(state: State) -> State:
    """Ejecuta solo la tool prices_history."""
    print("[TOOL] Ejecutando: prices_history")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_history],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] prices_history completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- prices_history ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "pricing",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }


async def node_prices_changes(state: State) -> State:
    """Ejecuta solo la tool prices_changes_last_n_days."""
    print("[TOOL] Ejecutando: prices_changes")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_changes_last_n_days],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] prices_changes completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- prices_changes ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "pricing",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }


async def node_prices_stats(state: State) -> State:
    """Ejecuta solo la tool prices_stats."""
    print("[TOOL] Ejecutando: prices_stats")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[prices_stats],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] prices_stats completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- prices_stats ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "pricing",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }


async def node_hits_quality(state: State) -> State:
    """Ejecuta solo la tool hits_with_quality."""
    print("[TOOL] Ejecutando: hits_quality")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[hits_with_quality],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] hits_quality completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- hits_quality ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "pricing",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

# Intelligence Tools Nodes


async def node_platform_exclusivity(state: State) -> State:
    """Ejecuta solo la tool get_platform_exclusivity_by_country."""
    print("[TOOL] Ejecutando: platform_exclusivity")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[get_platform_exclusivity_by_country],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] platform_exclusivity completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- platform_exclusivity ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "intelligence",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }


async def node_catalog_similarity(state: State) -> State:
    """Ejecuta solo la tool catalog_similarity_for_platform."""
    print("[TOOL] Ejecutando: catalog_similarity")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[catalog_similarity_for_platform],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] catalog_similarity completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- catalog_similarity ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "intelligence",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }


async def node_titles_diff(state: State) -> State:
    """Ejecuta solo la tool titles_in_A_not_in_B."""
    print("[TOOL] Ejecutando: titles_diff")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[titles_in_A_not_in_B],
        system_prompt=SYSTEM_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] titles_diff completada (tool #{count})")

    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- titles_diff ---\n{answer}" if prev_data else answer

    return {
        **state,
        "answer": answer,
        "task": "intelligence",
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

# ========== SUPERVISORES ==========


async def pricing_supervisor(state: State) -> State:
    """Supervisor que analiza si necesita más tools de pricing."""
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )

    supervisor_prompt = f"""Analiza si la información de pricing es suficiente.

    PREGUNTA ORIGINAL: {state['question']}
    TOOLS EJECUTADAS: {state.get('tool_calls_count', 0)}
    RESPUESTA ACTUAL: {state.get('answer', '')}

    ¿Necesitas más información de pricing o es suficiente?
    Responde SOLO: "SUFICIENTE" o "NECESITA_MAS"
    """

    response = llm.invoke(supervisor_prompt)
    decision = response.content.strip().upper()

    return {**state, "needs_more": "NECESITA_MAS" in decision}


async def intelligence_supervisor(state: State) -> State:
    """Supervisor que analiza si necesita más tools de intelligence."""
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )

    supervisor_prompt = f"""Analiza si la información de intelligence es suficiente.

    PREGUNTA ORIGINAL: {state['question']}
    TOOLS EJECUTADAS: {state.get('tool_calls_count', 0)}
    RESPUESTA ACTUAL: {state.get('answer', '')}

    ¿Necesitas más información de catálogo/plataformas o es suficiente?
    Responde SOLO: "SUFICIENTE" o "NECESITA_MAS"
    """

    response = llm.invoke(supervisor_prompt)
    decision = response.content.strip().upper()

    return {**state, "needs_more": "NECESITA_MAS" in decision}


async def main_supervisor(state: State) -> State:
    """
    Supervisor principal que:
    1. Clasifica la pregunta inicial (si no hay task definido)
    2. Coordina entre categorías si ya hay datos
    """
    print(
        f"[SUPERVISOR] Main supervisor analizando... task={state.get('task')}, tools={state.get('tool_calls_count', 0)}")

    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )

    # Si es la primera vez (no hay task), clasificar
    if not state.get("task"):
        print("[INFO] Primera clasificación de la pregunta")
        supervisor_prompt = f"""Clasifica esta pregunta y decide qué tipo de información necesita.

PREGUNTA: {state['question']}

CATEGORÍAS:
- PRICING: Preguntas sobre precios, costos, tarifas, cambios de precio, estadísticas de precio, histórico de precios
- INTELLIGENCE: Preguntas sobre catálogos, contenido disponible, exclusividad, comparación de plataformas, títulos disponibles, películas, series

IMPORTANTE: Responde SOLO con una de estas dos palabras exactas, sin explicaciones adicionales:
NECESITA_PRICING
NECESITA_INTELLIGENCE"""
    else:
        # Si ya hay datos, decidir si necesita más info
        print("[INFO] Evaluando si necesita más información")

        # Si ya se alcanzó el máximo de iteraciones, forzar COMPLETO
        if state.get('tool_calls_count', 0) >= state.get('max_iterations', 3):
            print("[WARNING] Máximo de iteraciones alcanzado, forzando COMPLETO")
            return {**state, "supervisor_decision": "COMPLETO"}

        supervisor_prompt = f"""Analiza CRÍTICAMENTE si ya tienes suficiente información para responder.

PREGUNTA ORIGINAL: {state['question']}
TOOLS EJECUTADAS: {state.get('tool_calls_count', 0)}/{state.get('max_iterations', 3)}

DATOS YA RECOPILADOS:
{state.get('accumulated_data', 'Ninguno')[:500]}...

REGLAS ESTRICTAS:
1. Si los datos YA RESPONDEN la pregunta (aunque sea parcialmente) -> COMPLETO
2. Si es una pregunta de comparación/lista y ya tienes títulos/datos -> COMPLETO
3. Solo marca NECESITA_* si falta información CRÍTICA que no está en los datos
4. NO pidas más datos solo para "completar" o "mejorar" la respuesta

EVALUACIÓN:
- ¿Los datos actuales responden la pregunta? SI/NO
- Si SI -> COMPLETO
- Si NO y faltan precios -> NECESITA_PRICING
- Si NO y faltan datos de catálogo -> NECESITA_INTELLIGENCE

IMPORTANTE: Responde SOLO con UNA palabra:
COMPLETO
NECESITA_PRICING
NECESITA_INTELLIGENCE"""

    response = llm.invoke(supervisor_prompt)
    decision_raw = response.content.strip().upper()
    # Extraer solo la primera línea (el LLM a veces añade explicaciones)
    decision = decision_raw.split('\n')[0].strip()
    print(f"[DECISION] Main supervisor decidió: '{decision}'")

    return {**state, "supervisor_decision": decision}


async def format_response(state: State) -> State:
    """Nodo final que formatea la respuesta."""
    formatter = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        tools=[],
        system_prompt=response_prompt
    )

    format_input = f"""Question: {state['question']}

    Raw data collected from multiple tools:
    {state.get('accumulated_data', state.get('answer', ''))}

    Format this response following the rules."""

    formatted = await formatter.invoke_async(format_input)
    final_answer = getattr(formatted, "message", str(formatted))

    return {
        "question": state["question"],
        "answer": final_answer,
        "task": state.get("task"),
        "tool_calls_count": state.get("tool_calls_count", 0)
    }

# ========== ROUTERS ==========


def route_from_main_supervisor(state: State) -> str:
    """
    Ruta desde main_supervisor a pricing, intelligence o format.
    El main_supervisor ahora también hace la clasificación inicial.
    """
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 3)
    decision = state.get("supervisor_decision", "COMPLETO").strip().upper()

    print(
        f"[ROUTING] Main supervisor routing: decision='{decision}', tools={count}/{max_iter}")

    if count >= max_iter:
        print("[ROUTE] Ruta: format_response (max iterations)")
        return "format_response"

    # Comparación exacta o por inclusión (por si el LLM añade texto)
    if decision == "NECESITA_PRICING" or "NECESITA_PRICING" in decision:
        print("[ROUTE] Ruta: router_pricing")
        return "router_pricing"
    elif decision == "NECESITA_INTELLIGENCE" or "NECESITA_INTELLIGENCE" in decision:
        print("[ROUTE] Ruta: router_intelligence")
        return "router_intelligence"
    else:
        print("[ROUTE] Ruta: format_response (completo)")
        return "format_response"


def route_pricing_tool(state: State) -> str:
    """Router que decide qué tool de pricing ejecutar."""
    print("[ROUTER] Pricing router: seleccionando tool...")
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )

    router_prompt = f"""Decide qué tool de pricing es la MEJOR para esta pregunta.

    PREGUNTA: {state['question']}
    DATOS PREVIOS: {state.get('accumulated_data', 'Ninguno')}

    TOOLS:
    - prices_latest: Precios actuales/últimos
    - prices_history: Histórico de precios
    - prices_changes: Cambios recientes (últimos N días)
    - prices_stats: Estadísticas (promedios, min, max)
    - hits_quality: Popularidad con filtros de calidad

    Responde SOLO el nombre: prices_latest, prices_history, prices_changes, prices_stats, o hits_quality
    """

    response = llm.invoke(router_prompt)
    tool_choice = response.content.strip().lower()

    if "changes" in tool_choice:
        print("[SELECT] Seleccionó: prices_changes")
        return "prices_changes"
    elif "history" in tool_choice:
        print("[SELECT] Seleccionó: prices_history")
        return "prices_history"
    elif "stats" in tool_choice:
        print("[SELECT] Seleccionó: prices_stats")
        return "prices_stats"
    elif "hits" in tool_choice or "quality" in tool_choice:
        print("[SELECT] Seleccionó: hits_quality")
        return "hits_quality"
    else:
        print("[SELECT] Seleccionó: prices_latest")
        return "prices_latest"


def route_intelligence_tool(state: State) -> str:
    """Router que decide qué tool de intelligence ejecutar."""
    print("[ROUTER] Intelligence router: seleccionando tool...")
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )

    router_prompt = f"""Decide qué tool de intelligence es la MEJOR para esta pregunta.

    PREGUNTA: {state['question']}
    DATOS PREVIOS: {state.get('accumulated_data', 'Ninguno')}

    TOOLS DISPONIBLES:
    - platform_exclusivity: Contenido EXCLUSIVO de UNA plataforma específica en un país (requiere nombre de plataforma)
    - catalog_similarity: Compara similitud del catálogo de UNA plataforma entre DOS países específicos
    - titles_diff: Lista títulos que están en plataforma A país X pero NO en plataforma B país Y

    IMPORTANTE:
    - Si la pregunta pide COMPARAR contenido TOTAL entre VARIAS plataformas -> NINGUNA TOOL ES APROPIADA -> usa "platform_exclusivity" (fallback)
    - Si la pregunta especifica UNA plataforma y UN país -> platform_exclusivity
    - Si la pregunta compara DOS países para UNA plataforma -> catalog_similarity  
    - Si la pregunta pide diferencias entre catálogos -> titles_diff

    Responde SOLO el nombre: platform_exclusivity, catalog_similarity, o titles_diff
    """

    response = llm.invoke(router_prompt)
    tool_choice = response.content.strip().lower()

    if "similarity" in tool_choice:
        print("[SELECT] Seleccionó: catalog_similarity")
        return "catalog_similarity"
    elif "diff" in tool_choice or "not in" in tool_choice:
        print("[SELECT] Seleccionó: titles_diff")
        return "titles_diff"
    else:
        print("[SELECT] Seleccionó: platform_exclusivity")
        return "platform_exclusivity"


def should_continue_pricing(state: State) -> str:
    """Decide si pricing supervisor continúa o va al main."""
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 3)
    needs_more = state.get("needs_more", False)

    if count >= max_iter:
        return "main_supervisor"

    if needs_more:
        return "router_pricing"

    return "main_supervisor"


def should_continue_intelligence(state: State) -> str:
    """Decide si intelligence supervisor continúa o va al main."""
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 3)
    needs_more = state.get("needs_more", False)

    if count >= max_iter:
        return "main_supervisor"

    if needs_more:
        return "router_intelligence"

    return "main_supervisor"


def should_continue_main(state: State) -> str:
    """Ya no se usa - la lógica está en route_from_main_supervisor."""
    return "format_response"


# ========== CONSTRUCCIÓN DEL GRAFO ==========
graph = StateGraph(State)

# Nodos individuales de pricing tools
graph.add_node("prices_latest", node_prices_latest)
graph.add_node("prices_history", node_prices_history)
graph.add_node("prices_changes", node_prices_changes)
graph.add_node("prices_stats", node_prices_stats)
graph.add_node("hits_quality", node_hits_quality)

# Nodos individuales de intelligence tools
graph.add_node("platform_exclusivity", node_platform_exclusivity)
graph.add_node("catalog_similarity", node_catalog_similarity)
graph.add_node("titles_diff", node_titles_diff)

# Nodos de routing y supervisión (SIN CLASSIFIER y SIN supervisores intermedios)
graph.add_node("router_pricing", lambda s: s)
graph.add_node("router_intelligence", lambda s: s)
graph.add_node("main_supervisor", main_supervisor)
graph.add_node("format_response", format_response)

# Flujo: START -> main_supervisor (clasifica Y supervisa)
graph.add_edge(START, "main_supervisor")

# Main supervisor decide dónde ir
graph.add_conditional_edges(
    "main_supervisor",
    route_from_main_supervisor,
    {
        "router_pricing": "router_pricing",
        "router_intelligence": "router_intelligence",
        "format_response": "format_response"
    }
)

# Router pricing -> tools
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

# Router intelligence -> tools
graph.add_conditional_edges(
    "router_intelligence",
    route_intelligence_tool,
    {
        "platform_exclusivity": "platform_exclusivity",
        "catalog_similarity": "catalog_similarity",
        "titles_diff": "titles_diff"
    }
)

# Pricing tools -> DIRECTO al main_supervisor (sin supervisor intermedio)
graph.add_edge("prices_latest", "main_supervisor")
graph.add_edge("prices_history", "main_supervisor")
graph.add_edge("prices_changes", "main_supervisor")
graph.add_edge("prices_stats", "main_supervisor")
graph.add_edge("hits_quality", "main_supervisor")

# Intelligence tools -> DIRECTO al main_supervisor (sin supervisor intermedio)
graph.add_edge("platform_exclusivity", "main_supervisor")
graph.add_edge("catalog_similarity", "main_supervisor")
graph.add_edge("titles_diff", "main_supervisor")

# format_response -> END
graph.add_edge("format_response", END)

app = graph.compile()

# ========== TESTING ==========

if __name__ == "__main__":
    print("\n" + "="*60)
    print("GRAFO CON NODOS INDIVIDUALES POR TOOL")
    print("="*60)

    # Imprimir diagrama del grafo
    try:
        print("DIAGRAMA MERMAID DEL GRAFO:")
        print("="*60)
        mermaid_code = app.get_graph().draw_mermaid()
        print(mermaid_code)
        print("="*60 + "\n")
        print("Copia el código Mermaid en https://mermaid.live para visualizarlo\n")
    except Exception as e:
        print(f"[WARNING] No se pudo generar diagrama mermaid: {e}\n")

    # Imprimir nodos y edges del grafo
    try:
        print("RESUMEN DEL GRAFO:")
        print("="*60)
        graph_dict = app.get_graph().to_json()
        print(
            f"Nodos ({len(graph_dict.get('nodes', []))}): {[n['id'] for n in graph_dict.get('nodes', [])]}")
        print(f"\nEdges: {len(graph_dict.get('edges', []))}")
        for edge in graph_dict.get('edges', [])[:15]:  # Primeros 15 edges
            print(f"  - {edge.get('source')} → {edge.get('target')}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"[WARNING] No se pudo obtener resumen: {e}\n")

    async def ask(q: str, task: str | None = None, max_iterations: int = 1):
        payload = {
            "question": q,
            "tool_calls_count": 0,
            "max_iterations": max_iterations
        }
        if task:
            payload["task"] = task

        start_time = time.time()
        result = await app.ainvoke(payload)
        elapsed_time = time.time() - start_time

        print(f"\n[QUERY] Pregunta: {q}")
        print(f"[TIME] Tiempo: {elapsed_time:.2f}s")
        print(f"[TOOLS] Tools: {result.get('tool_calls_count', 0)}")
        print(f"[RESPONSE] Respuesta:\n{result.get('answer', 'No answer')}\n")
        return result

    async def main():
        await ask("Que plataforma tiene mas contenido disponible en US.")
        await ask("Que peliculas tiene Netflix en US que no en MX.")

    asyncio.run(main())
