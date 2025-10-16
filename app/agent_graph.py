import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import re
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langchain_aws.chat_models import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from typing import TypedDict

from src.sql.modules.common.validation import validate_title, validate_actor, validate_director
from src.sql.modules.content.discovery import get_filmography_by_uid, get_title_rating
from src.sql.modules.platform.availability import get_availability_by_uid
from src.sql.modules.platform.presence import presence_list
from src.sql.modules.talent.actors import get_actor_filmography
from src.sql.modules.talent.directors import get_director_filmography


# Configuración del LLM (Bedrock Haiku 3.5)
validation_llm = ChatBedrock(model="us.anthropic.claude-3-5-sonnet-20241022-v2:0", region="us-east-1")
planning_llm = ChatBedrock(model="us.anthropic.claude-3-5-sonnet-20241022-v2:0", region="us-east-1")
answer_llm = ChatBedrock(model="us.anthropic.claude-3-5-sonnet-20241022-v2:0", region="us-east-1")


validation_tools = {
    "validate_title": validate_title,
    "validate_actor": validate_actor,
    "validate_director": validate_director
}


tools = {
    "get_filmography_by_uid": get_filmography_by_uid,
    "get_title_rating": get_title_rating,
    "get_availability_by_uid": get_availability_by_uid,
    "presence_list": presence_list,
    "get_actor_filmography": get_actor_filmography,
    "get_director_filmography": get_director_filmography,
}


class State(TypedDict):
    messages: list[BaseMessage]
    plan: list[dict]
    validation_plan: list[dict]
    validation_results: dict[str, str]
    tool_results: dict[str, str]
    output: str


def parse_plan(plan_text: str):
    try:
        data = json.loads(plan_text)
        return data.get("steps", [])
    except json.JSONDecodeError:
        raise ValueError(f"Respuesta del planner no es JSON válido:\n{plan_text}")


def substitute_placeholders(args, results):
    """
    Reemplaza placeholders tipo:
      {{step_1}} -> resultado completo del paso 1
      {{step_1.uid}} -> valor de la clave 'uid' dentro del resultado del paso 1
    """
    def resolve_placeholder(path):
        parts = path.split(".")
        value = results.get(parts[0])
        for key in parts[1:]:  # recorrer las claves anidadas
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return f"{{{{{path}}}}}"  # fallback si no existe
        return value

    def replace(match):
        path = match.group(1)
        value = resolve_placeholder(path)
        return str(value) if value is not None else f"{{{{{path}}}}}"

    if isinstance(args, str):
        return re.sub(r"\{\{(.*?)\}\}", replace, args)
    if isinstance(args, dict):
        return {k: substitute_placeholders(v, results) for k, v in args.items()}
    if isinstance(args, list):
        return [substitute_placeholders(v, results) for v in args]
    return args

# Nodo de validacion de nombres y titulos
def validate_node(state: State):
    with open("./prompts/validation.txt", encoding="utf-8") as file:
        plan_prompt = file.read()
    messages = [SystemMessage(content=plan_prompt)] + state['messages']
    plan = validation_llm.invoke(messages).content
    state['validation_plan'] = parse_plan(plan)
    print(state)
    return state


# Ejecuta las validaciones consultando al usuario cuando hay ambigüedad
def execute_validation_node(state: State):
    results = {}

    for i, step in enumerate(state['validation_plan'], 1):
        step_key = f"step_{i}"
        tool_name = step["tool_name"]

        tool = validation_tools.get(tool_name)
        if not tool:
            results[step_key] = f"Unknown tool: {tool_name}"
            continue

        result = tool(**step["args"])
        if result["status"] == "ambiguous":
            selected_index = interrupt({"options": result["options"]})
            result = result["options"][selected_index]
        else:
            result = result["result"]

        results[step_key] = result

        step["result"] = result
        state['messages'] += [HumanMessage(content=str(step))]
        print(step)

    state['validation_results'] = results
    return state


# Nodo de planificación: llama al LLM para generar el plan (qué tools usar)
def plan_node(state: State):
    with open("./prompts/planning.txt", encoding="utf-8") as file:
        plan_prompt = file.read()
    messages = [SystemMessage(content=plan_prompt)] + state['messages']
    plan = planning_llm.invoke(messages).content
    state['plan'] = parse_plan(plan)
    print(state)
    return state


# Nodo de ejecución: ejecuta cada tool del plan
def execute_node(state: State):
    results = {}

    for i, step in enumerate(state['plan'], 1):
        step_key = f"step_{i}"
        tool_name = step["tool_name"]

        step["args"] = substitute_placeholders(step["args"], results)

        tool = tools.get(tool_name)
        if not tool:
            results[step_key] = f"Unknown tool: {tool_name}"
            continue

        result = tool(**step["args"])
        results[step_key] = result

        step["result"] = result
        state['messages'] += [HumanMessage(content=str(step))]
        print(step)

    state['tool_results'] = results
    return state


# Nodo de respuesta final: llama al LLM para generar la respuesta final
def answer_node(state: State):
    with open("./prompts/answer.txt", encoding="utf-8") as file:
        answer_prompt = file.read()
    messages = [SystemMessage(content=answer_prompt)] + state['messages']
    answer = answer_llm.invoke(messages).content
    state['output'] = answer
    state['messages'] += [AIMessage(content=answer)]
    return state


# Construcción del grafo
graph = StateGraph(state_schema=State)
graph.add_node("validate", validate_node)
graph.add_node("execute_validation", execute_validation_node)
graph.add_node("plan", plan_node)
graph.add_node("execute", execute_node)
graph.add_node("answer", answer_node)

graph.add_edge(START, "validate")
graph.add_edge("validate", "execute_validation")
graph.add_edge("execute_validation", "plan")
graph.add_edge("plan", "execute")
graph.add_edge("execute", "answer")
graph.add_edge("answer", END)

checkpointer = InMemorySaver()
agent = graph.compile(checkpointer=checkpointer)
