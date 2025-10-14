import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import re
from langgraph.graph import StateGraph, START, END
from langchain_aws.chat_models import ChatBedrock
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from typing import TypedDict

from src.sql.modules.common.validation import validate_title
from src.sql.modules.content.discovery import get_filmography_by_uid, get_title_rating
from src.sql.modules.platform.availability import get_availability_by_uid
from src.sql.modules.platform.presence import presence_list
from src.sql.modules.talent.actors import get_actor_filmography, get_actor_filmography_by_name
from src.sql.modules.talent.directors import get_director_filmography, get_director_filmography_by_name


# Configuración del LLM (Bedrock Haiku 3.5)
llm = ChatBedrock(model="us.anthropic.claude-3-5-haiku-20241022-v1:0", region="us-east-1")


def pick_title(title, threshold=None):
    result = validate_title(title, threshold)
    if result['status'] == 'ambiguous':
        return result['options'][0]
    elif result['status'] == 'resolved':
        return result['result']
    else:
        return None


tools = {
    "validate_title": pick_title,
    "get_filmography_by_uid": get_filmography_by_uid,
    "get_title_rating": get_title_rating,
    "get_availability_by_uid": get_availability_by_uid,
    "presence_list": presence_list,
    "get_actor_filmography": get_actor_filmography,
    "get_actor_filmography_by_name": get_actor_filmography_by_name,
    "get_director_filmography": get_director_filmography,
    "get_director_filmography_by_name": get_director_filmography_by_name,
}


class State(TypedDict):
    messages: list[BaseMessage]
    plan: list[dict]
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


# Nodo de planificación: llama al LLM para generar el plan (qué tools usar)
def plan_node(state: State):
    with open("./prompts/planning.txt", encoding="utf-8") as file:
        plan_prompt = file.read()
    messages = [SystemMessage(content=plan_prompt)] + state['messages']
    plan = llm.invoke(messages).content
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
    answer = llm.invoke(messages).content
    state['output'] = answer
    state['messages'] += [AIMessage(content=answer)]
    return state


# Construcción del grafo
graph = StateGraph(state_schema=State)
graph.add_node("plan", plan_node)
graph.add_node("execute", execute_node)
graph.add_node("answer", answer_node)

graph.add_edge(START, "plan")
graph.add_edge("plan", "execute")
graph.add_edge("execute", "answer")
graph.add_edge("answer", END)

agent = graph.compile()
