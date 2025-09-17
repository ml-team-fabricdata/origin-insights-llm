from typing import Union
from src.sql_db import db
from queries import *
from db_utils_sql import *
from constants_sql import *


def get_actor_filmography(actor_id: int, limit: int = DEFAULT_LIMIT) -> str:
    """
    Obtiene la filmografía de un actor.

    Args:
        actor_id: ID del actor
        limit: Límite de resultados

    Returns:
        JSON string con la filmografía
    """
    validated_limit = validate_limit(limit)

    try:
        results = db.execute_query(
            FILMOGRAPHY_SQL_ACTOR, (actor_id, validated_limit))
        handled_results = handle_query_result(
            results, "actor_filmography", str(actor_id))
        return json.dumps(handled_results, indent=2)
    except Exception as e:
        logger.error(f"Error getting actor filmography for ID {actor_id}: {e}")
        return json.dumps({"error": f"Failed to get filmography: {str(e)}"}, indent=2)


def get_actor_coactors(actor_id: int, limit: int = MAX_LIMIT) -> str:
    """
    Obtiene los co-actores de un actor.

    Args:
        actor_id: ID del actor
        limit: Límite de resultados

    Returns:
        JSON string con los co-actores
    """
    validated_limit = validate_limit(limit, max_limit=MAX_LIMIT)

    try:
        results = db.execute_query(
            COACTORS_SQL, (actor_id, actor_id, validated_limit))
        handled_results = handle_query_result(
            results, "actor_coactors", str(actor_id))
        return json.dumps(handled_results, indent=2)
    except Exception as e:
        logger.error(f"Error getting actor coactors for ID {actor_id}: {e}")
        return json.dumps({"error": f"Failed to get coactors: {str(e)}"}, indent=2)


def answer_actor_filmography(actor_name: Union[str, List[str], Any], limit: int = DEFAULT_LIMIT) -> str:
    """
    Flujo de alto nivel: validar → filmografía.

    Args:
        actor_name: Nombre del actor
        limit: Límite de resultados

    Returns:
        String con la filmografía o mensaje de ambigüedad/error
    """
    validation = validate_actor(actor_name)

    if validation["status"] == "ok":
        return get_actor_filmography(validation["id"], limit)
    elif validation["status"] == "ambiguous":
        options_text = "\n".join(
            f"- {opt['name']} (id {opt['id']}" +
            (f", score {opt['score']:.2f}" if opt.get("score") else "") + ")"
            for opt in validation["options"]
        )
        query_text = normalize_name_input(actor_name)
        return f"Encontré varios posibles para {query_text}. Elige uno:\n{options_text}"
    else:
        query_text = normalize_name_input(actor_name)
        return f"No encontré coincidencias para {query_text}."


def answer_actor_coactors(actor_name: Union[str, List[str], Any], limit: int = 25) -> str:
    """
    Flujo de alto nivel: validar → co-actores.

    Args:
        actor_name: Nombre del actor
        limit: Límite de resultados

    Returns:
        String con los co-actores o mensaje de ambigüedad/error
    """
    validation = validate_actor(actor_name)

    if validation["status"] == "ok":
        return get_actor_coactors(validation["id"], limit)
    elif validation["status"] == "ambiguous":
        options_text = "\n".join(
            f"- {opt['name']} (id {opt['id']}" +
            (f", score {opt['score']:.2f}" if opt.get("score") else "") + ")"
            for opt in validation["options"]
        )
        query_text = _normalize_name_input(actor_name)
        return f"Encontré varios posibles para {query_text}. Elige uno:\n{options_text}"
    else:
        query_text = _normalize_name_input(actor_name)
        return f"No encontré coincidencias para {query_text}."
