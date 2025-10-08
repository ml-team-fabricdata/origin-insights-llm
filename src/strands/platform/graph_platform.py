# -*- coding: utf-8 -*-
# graph_platform.py - Grafo LangGraph para módulo Platform
import sys
from pathlib import Path

# Agregar el directorio raíz al path ANTES de cualquier import
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

import asyncio
import time
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from strands import Agent
from langchain_aws import ChatBedrock

# Importar prompts y tools
from src.strands.platform.prompt_platform import AVAILABILITY_PROMPT, PRESENCE_PROMPT

# Importar todas las tools
from src.sql.modules.platform.availability import (
    get_availability_by_uid, get_platform_exclusives, 
    compare_platforms_for_title, get_recent_premieres_by_country
)
from src.sql.modules.platform.presence import (
    presence_count, presence_list, presence_distinct, 
    presence_statistics, platform_count_by_country, country_platform_summary
)
from src.prompt_templates.prompt import response_prompt

# ========== STATE ==========

class State(TypedDict, total=False):
    question: str
    answer: str
    task: Literal["availability", "presence"]
    tool_calls_count: int
    max_iterations: int
    accumulated_data: str
    supervisor_decision: str
    needs_more: bool

# ========== NODOS INDIVIDUALES PARA CADA TOOL ==========

# Availability Tools
async def node_availability_by_uid(state: State) -> State:
    """Ejecuta get_availability_by_uid."""
    print("[TOOL] Ejecutando: availability_by_uid")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[get_availability_by_uid],
        system_prompt=AVAILABILITY_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] availability_by_uid completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- availability_by_uid ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "availability", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_platform_exclusives(state: State) -> State:
    """Ejecuta get_platform_exclusives."""
    print("[TOOL] Ejecutando: platform_exclusives")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[get_platform_exclusives],
        system_prompt=AVAILABILITY_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] platform_exclusives completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- platform_exclusives ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "availability", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_compare_platforms(state: State) -> State:
    """Ejecuta compare_platforms_for_title."""
    print("[TOOL] Ejecutando: compare_platforms")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[compare_platforms_for_title],
        system_prompt=AVAILABILITY_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] compare_platforms completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- compare_platforms ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "availability", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_recent_premieres(state: State) -> State:
    """Ejecuta get_recent_premieres_by_country."""
    print("[TOOL] Ejecutando: recent_premieres")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[get_recent_premieres_by_country],
        system_prompt=AVAILABILITY_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] recent_premieres completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- recent_premieres ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "availability", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

# Presence Tools
async def node_presence_count(state: State) -> State:
    """Ejecuta presence_count."""
    print("[TOOL] Ejecutando: presence_count")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[presence_count],
        system_prompt=PRESENCE_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] presence_count completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- presence_count ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "presence", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_presence_list(state: State) -> State:
    """Ejecuta presence_list."""
    print("[TOOL] Ejecutando: presence_list")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[presence_list],
        system_prompt=PRESENCE_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] presence_list completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- presence_list ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "presence", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_presence_statistics(state: State) -> State:
    """Ejecuta presence_statistics."""
    print("[TOOL] Ejecutando: presence_statistics")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[presence_statistics],
        system_prompt=PRESENCE_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] presence_statistics completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- presence_statistics ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "presence", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_platform_count_by_country(state: State) -> State:
    """Ejecuta platform_count_by_country."""
    print("[TOOL] Ejecutando: platform_count_by_country")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[platform_count_by_country],
        system_prompt=PRESENCE_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] platform_count_by_country completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- platform_count_by_country ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "presence", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

async def node_country_platform_summary(state: State) -> State:
    """Ejecuta country_platform_summary."""
    print("[TOOL] Ejecutando: country_platform_summary")
    q = state["question"]
    agent = Agent(
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        tools=[country_platform_summary],
        system_prompt=PRESENCE_PROMPT
    )
    result = await agent.invoke_async(q)
    answer = getattr(result, "message", str(result))
    count = state.get("tool_calls_count", 0) + 1
    print(f"[OK] country_platform_summary completada (tool #{count})")
    
    prev_data = state.get("accumulated_data", "")
    accumulated = f"{prev_data}\n\n--- country_platform_summary ---\n{answer}" if prev_data else answer
    
    return {
        **state, 
        "answer": answer, 
        "task": "presence", 
        "tool_calls_count": count,
        "accumulated_data": accumulated
    }

# ========== NODO PLATFORM CLASSIFIER ==========

async def platform_classifier(state: State) -> State:
    """Nodo clasificador inicial que determina si es AVAILABILITY o PRESENCE."""
    print(f"[PLATFORM] Clasificando pregunta...")
    
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    classifier_prompt = f"""Clasifica esta pregunta sobre plataformas de streaming.

PREGUNTA: {state['question']}

CATEGORIAS:
- AVAILABILITY: Preguntas sobre disponibilidad de titulos especificos, exclusivos de plataformas, comparacion de donde ver un titulo, estrenos recientes
- PRESENCE: Preguntas sobre conteos, estadisticas generales, listados con filtros, resumen de plataformas por pais, cuantas plataformas hay

IMPORTANTE: Responde SOLO con una de estas dos palabras:
AVAILABILITY
PRESENCE"""
    
    response = llm.invoke(classifier_prompt)
    decision = response.content.strip().upper()
    print(f"[PLATFORM] Clasificacion inicial: '{decision}'")
    
    return {**state, "task": decision.lower() if decision in ["AVAILABILITY", "PRESENCE"] else None}

# ========== SUPERVISOR PRINCIPAL ==========

async def main_supervisor(state: State) -> State:
    """
    Supervisor principal que:
    1. Decide si necesita más información o si está completo
    2. Coordina el flujo entre tools
    """
    print(f"[SUPERVISOR] Main supervisor analizando... task={state.get('task')}, tools={state.get('tool_calls_count', 0)}")
    
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    # Si es la primera vez (no hay tools ejecutadas), necesita clasificación
    if state.get("tool_calls_count", 0) == 0:
        print("[INFO] Primera vez, necesita clasificacion")
        # El task ya viene del platform_classifier si viene de ahí, sino se define
        if state.get("task"):
            decision = f"NECESITA_{state.get('task', '').upper()}"
        else:
            # Por defecto, necesita ir al classifier
            decision = "NECESITA_AVAILABILITY"
        print(f"[DECISION] Main supervisor decidio: '{decision}'")
        return {**state, "supervisor_decision": decision}
    
    # Si ya hay datos, decidir si necesita más info
    print("[INFO] Evaluando si necesita mas informacion")
    
    # Si ya se alcanzó el máximo de iteraciones, forzar COMPLETO
    if state.get('tool_calls_count', 0) >= state.get('max_iterations', 1):
        print("[WARNING] Maximo de iteraciones alcanzado, forzando COMPLETO")
        return {**state, "supervisor_decision": "COMPLETO"}
    
    supervisor_prompt = f"""Analiza CRITICAMENTE si ya tienes suficiente informacion para responder.

PREGUNTA ORIGINAL: {state['question']}
TOOLS EJECUTADAS: {state.get('tool_calls_count', 0)}/{state.get('max_iterations', 1)}

DATOS YA RECOPILADOS:
{state.get('accumulated_data', 'Ninguno')[:500]}...

REGLAS ESTRICTAS:
1. Si los datos YA RESPONDEN la pregunta (aunque sea parcialmente) -> COMPLETO
2. Si es una pregunta de listado y ya tienes datos -> COMPLETO
3. Solo marca NECESITA_* si falta informacion CRITICA que no esta en los datos
4. NO pidas mas datos solo para "completar" o "mejorar" la respuesta

IMPORTANTE: Responde SOLO con UNA palabra:
COMPLETO
NECESITA_AVAILABILITY
NECESITA_PRESENCE"""
    
    response = llm.invoke(supervisor_prompt)
    decision_raw = response.content.strip().upper()
    # Extraer solo la primera línea (el LLM a veces añade explicaciones)
    decision = decision_raw.split('\n')[0].strip()
    print(f"[DECISION] Main supervisor decidio: '{decision}'")
    
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
    """Ruta desde main_supervisor a platform_classifier o format."""
    count = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 1)
    decision = state.get("supervisor_decision", "COMPLETO").strip().upper()
    
    print(f"[ROUTING] Main supervisor routing: decision='{decision}', tools={count}/{max_iter}")
    
    if count >= max_iter:
        print("[ROUTE] Ruta: format_response (max iterations)")
        return "format_response"
    
    # Si necesita datos, ir al platform_classifier
    if decision == "NECESITA_AVAILABILITY" or "NECESITA_AVAILABILITY" in decision:
        print("[ROUTE] Ruta: platform_classifier (availability)")
        return "platform_classifier"
    elif decision == "NECESITA_PRESENCE" or "NECESITA_PRESENCE" in decision:
        print("[ROUTE] Ruta: platform_classifier (presence)")
        return "platform_classifier"
    else:
        print("[ROUTE] Ruta: format_response (completo)")
        return "format_response"

def route_availability_tool(state: State) -> str:
    """Router que decide qué tool de availability ejecutar."""
    print("[ROUTER] Availability router: seleccionando tool...")
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    router_prompt = f"""Decide que tool de availability es la MEJOR para esta pregunta.

    PREGUNTA: {state['question']}
    DATOS PREVIOS: {state.get('accumulated_data', 'Ninguno')}

    TOOLS:
    - availability_by_uid: Disponibilidad de un titulo especifico por UID
    - platform_exclusives: Titulos exclusivos de una plataforma en un pais/region
    - compare_platforms: Comparar en que plataformas esta disponible un titulo
    - recent_premieres: Estrenos recientes (ultimos 7 dias) por pais

    Responde SOLO el nombre: availability_by_uid, platform_exclusives, compare_platforms, o recent_premieres
    """
        
    response = llm.invoke(router_prompt)
    tool_choice = response.content.strip().lower()
    
    if "uid" in tool_choice or "availability_by_uid" in tool_choice:
        print("[SELECT] Selecciono: availability_by_uid")
        return "availability_by_uid"
    elif "exclusive" in tool_choice or "platform_exclusives" in tool_choice:
        print("[SELECT] Selecciono: platform_exclusives")
        return "platform_exclusives"
    elif "compare" in tool_choice or "compare_platforms" in tool_choice:
        print("[SELECT] Selecciono: compare_platforms")
        return "compare_platforms"
    else:
        print("[SELECT] Selecciono: recent_premieres")
        return "recent_premieres"

def route_presence_tool(state: State) -> str:
    """Router que decide qué tool de presence ejecutar."""
    print("[ROUTER] Presence router: seleccionando tool...")
    llm = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0
    )
    
    router_prompt = f"""Decide que tool de presence es la MEJOR para esta pregunta.

    PREGUNTA: {state['question']}
    DATOS PREVIOS: {state.get('accumulated_data', 'Ninguno')}

    TOOLS:
    - presence_count: Conteo rapido de presencia
    - presence_list: Listado paginado con filtros y orden
    - presence_statistics: Estadisticas completas de presencia
    - platform_count_by_country: Conteo de plataformas por pais
    - country_platform_summary: Resumen detallado de plataformas por pais/region

    Responde SOLO el nombre: presence_count, presence_list, presence_statistics, platform_count_by_country, o country_platform_summary
    """
    
    response = llm.invoke(router_prompt)
    tool_choice = response.content.strip().lower()
    
    if "count" in tool_choice and "platform" in tool_choice:
        print("[SELECT] Selecciono: platform_count_by_country")
        return "platform_count_by_country"
    elif "summary" in tool_choice or "country_platform" in tool_choice:
        print("[SELECT] Selecciono: country_platform_summary")
        return "country_platform_summary"
    elif "statistics" in tool_choice or "stats" in tool_choice:
        print("[SELECT] Selecciono: presence_statistics")
        return "presence_statistics"
    elif "list" in tool_choice:
        print("[SELECT] Selecciono: presence_list")
        return "presence_list"
    else:
        print("[SELECT] Selecciono: presence_count")
        return "presence_count"

# ========== CONSTRUCCION DEL GRAFO ==========
graph = StateGraph(State)

# Nodos de availability tools
graph.add_node("availability_by_uid", node_availability_by_uid)
graph.add_node("platform_exclusives", node_platform_exclusives)
graph.add_node("compare_platforms", node_compare_platforms)
graph.add_node("recent_premieres", node_recent_premieres)

# Nodos de presence tools
graph.add_node("presence_count", node_presence_count)
graph.add_node("presence_list", node_presence_list)
graph.add_node("presence_statistics", node_presence_statistics)
graph.add_node("platform_count_by_country", node_platform_count_by_country)
graph.add_node("country_platform_summary", node_country_platform_summary)

# Nodos de routing y supervision
graph.add_node("platform_classifier", platform_classifier)
graph.add_node("router_availability", lambda s: s)
graph.add_node("router_presence", lambda s: s)
graph.add_node("main_supervisor", main_supervisor)
graph.add_node("format_response", format_response)

# Flujo: START -> main_supervisor -> platform_classifier -> routers
graph.add_edge(START, "main_supervisor")

# Main supervisor decide donde ir (a platform_classifier o format_response)
graph.add_conditional_edges(
    "main_supervisor",
    route_from_main_supervisor,
    {
        "platform_classifier": "platform_classifier",
        "format_response": "format_response"
    }
)

# Platform classifier decide entre availability o presence
def route_from_platform_classifier(state: State) -> str:
    """Ruta desde platform_classifier a los routers."""
    task = state.get("task", "").lower()
    print(f"[ROUTING] Platform classifier routing: task='{task}'")
    
    if task == "availability":
        print("[ROUTE] Ruta: router_availability")
        return "router_availability"
    elif task == "presence":
        print("[ROUTE] Ruta: router_presence")
        return "router_presence"
    else:
        # Fallback si no hay task definida
        print("[ROUTE] Ruta: router_presence (fallback)")
        return "router_presence"

graph.add_conditional_edges(
    "platform_classifier",
    route_from_platform_classifier,
    {
        "router_availability": "router_availability",
        "router_presence": "router_presence"
    }
)

# Router availability -> tools
graph.add_conditional_edges(
    "router_availability",
    route_availability_tool,
    {
        "availability_by_uid": "availability_by_uid",
        "platform_exclusives": "platform_exclusives",
        "compare_platforms": "compare_platforms",
        "recent_premieres": "recent_premieres"
    }
)

# Router presence -> tools
graph.add_conditional_edges(
    "router_presence",
    route_presence_tool,
    {
        "presence_count": "presence_count",
        "presence_list": "presence_list",
        "presence_statistics": "presence_statistics",
        "platform_count_by_country": "platform_count_by_country",
        "country_platform_summary": "country_platform_summary"
    }
)

# Availability tools -> DIRECTO al main_supervisor
graph.add_edge("availability_by_uid", "main_supervisor")
graph.add_edge("platform_exclusives", "main_supervisor")
graph.add_edge("compare_platforms", "main_supervisor")
graph.add_edge("recent_premieres", "main_supervisor")

# Presence tools -> DIRECTO al main_supervisor
graph.add_edge("presence_count", "main_supervisor")
graph.add_edge("presence_list", "main_supervisor")
graph.add_edge("presence_statistics", "main_supervisor")
graph.add_edge("platform_count_by_country", "main_supervisor")
graph.add_edge("country_platform_summary", "main_supervisor")

# format_response -> END
graph.add_edge("format_response", END)

app = graph.compile()

# ========== TESTING ==========

if __name__ == "__main__":
    print("\n" + "="*60)
    print("GRAFO PLATFORM - AVAILABILITY & PRESENCE")
    print("="*60)
    print("""
    Estructura:
    START -> main_supervisor (coordina)
              |
              v
          platform_classifier (clasifica: AVAILABILITY o PRESENCE)
              |
    router_availability -> [4 tools] -> main_supervisor
              |
    router_presence -> [5 tools] -> main_supervisor
              |
    format_response -> END
    
    Flujo:
    1. main_supervisor: Decide si necesita datos
    2. platform_classifier: Clasifica tipo de informacion
    3. routers: Seleccion de tool especifica
    4. tools: Ejecucion
    5. main_supervisor: Loop o terminar
    6. format_response: Formato final
    """)
    print("="*60 + "\n")
    
    # Imprimir diagrama del grafo
    try:
        print("DIAGRAMA MERMAID DEL GRAFO:")
        print("="*60)
        mermaid_code = app.get_graph().draw_mermaid()
        print(mermaid_code)
        print("="*60 + "\n")
        print("Copia el codigo Mermaid en https://mermaid.live para visualizarlo\n")
    except Exception as e:
        print(f"[WARNING] No se pudo generar diagrama mermaid: {e}\n")
    
    # Imprimir nodos y edges del grafo
    try:
        print("RESUMEN DEL GRAFO:")
        print("="*60)
        graph_dict = app.get_graph().to_json()
        print(f"Nodos ({len(graph_dict.get('nodes', []))}): {[n['id'] for n in graph_dict.get('nodes', [])]}")
        print(f"\nEdges: {len(graph_dict.get('edges', []))}")
        for edge in graph_dict.get('edges', [])[:20]:
            print(f"  - {edge.get('source')} -> {edge.get('target')}")
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
        # Ejemplos de preguntas para platform
        await ask("Cuantas plataformas hay en Argentina?")
    
    asyncio.run(main())
