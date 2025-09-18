from typing import Dict, Any, List, Optional, Union
from src.sql.constants_sql import *
from src.sql.db_utils_sql import *


class ValidationResult:
    @staticmethod
    def not_found() -> Dict[str, Any]:
        return {"status": "not_found"}
    
    @staticmethod
    def resolved(result: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "resolved", "result": result}
    
    @staticmethod
    def ambiguous(options: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"status": "ambiguous", "options": options}
    
    @staticmethod
    def ok(entity_id: str, name: str) -> Dict[str, Any]:
        return {"status": "ok", "id": entity_id, "name": name}

def validate_title_sync(title: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Validación síncrona ultra-rápida de títulos"""
    normalized_query = normalize_input(title)
    if not normalized_query:
        return ValidationResult.not_found()
    
    normalized_query = clean_text(normalized_query)
    if not normalized_query:
        return ValidationResult.not_found()
    
    # Búsqueda exacta primero
    exact_results = db_sync.execute_query(EXACT_SEARCH_SQL, (normalized_query,))
    
    if exact_results:
        if len(exact_results) == 1:
            result = {
                "uid": exact_results[0].get('uid'),
                "title": exact_results[0].get('title'),
                "year": exact_results[0].get('year'),
                "type": exact_results[0].get('type'),
                "imdb_id": exact_results[0].get('imdb_id')
            }
            return ValidationResult.resolved(result)
        
        # Múltiples exactos - devolver opciones
        options = []
        for result in exact_results[:8]:
            options.append({
                "uid": result.get('uid'),
                "title": result.get('title'),
                "year": result.get('year'),
                "type": result.get('type'),
                "imdb_id": result.get('imdb_id')
            })
        return ValidationResult.ambiguous(options)
    
    # Búsqueda fuzzy solo si no hay exactos
    threshold = normalize_threshold(threshold)
    params = (normalized_query, threshold, threshold, threshold, 12)
    
    fuzzy_results = db_sync.execute_query(FUZZY_SEARCH_SQL, params)
    
    if not fuzzy_results:
        return ValidationResult.not_found()
    
    if len(fuzzy_results) == 1 and not is_single_token(normalized_query):
        result = {
            "uid": fuzzy_results[0].get('uid'),
            "title": fuzzy_results[0].get('aka_title'),
            "year": fuzzy_results[0].get('year'),
            "type": fuzzy_results[0].get('type'),
            "imdb_id": fuzzy_results[0].get('imdb_id')
        }
        return ValidationResult.resolved(result)
    
    # Múltiples fuzzy - devolver opciones
    options = []
    for result in fuzzy_results[:8]:
        options.append({
            "uid": result.get('uid'),
            "title": result.get('aka_title'),
            "year": result.get('year'),
            "type": result.get('type'),
            "imdb_id": result.get('imdb_id')
        })
    
    return ValidationResult.ambiguous(options)

def validate_actor_sync(name: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Validación síncrona de actores"""
    normalized_query = normalize_input(name)
    if not normalized_query:
        return ValidationResult.not_found()
    
    # Búsqueda exacta
    exact_results = db_sync.execute_query(ACTOR_EXACT_SQL, (normalized_query,))
    
    if exact_results:
        if len(exact_results) == 1:
            result = exact_results[0]
            return ValidationResult.ok(result.get('id'), result.get('name'))
        
        options = []
        for result in exact_results[:5]:
            options.append({
                "id": result.get('id'),
                "name": result.get('name'),
                "score": 1.0
            })
        return ValidationResult.ambiguous(options)
    
    # Búsqueda fuzzy
    fuzzy_results = db_sync.execute_query(ACTOR_FUZZY_SQL_ILIKE, (normalized_query,))
    
    if not fuzzy_results:
        return ValidationResult.not_found()
    
    if len(fuzzy_results) == 1 and not is_single_token(normalized_query):
        result = fuzzy_results[0]
        return ValidationResult.ok(result.get('id'), result.get('name'))
    
    options = []
    for result in fuzzy_results[:5]:
        options.append({
            "id": result.get('id'),
            "name": result.get('name'),
            "score": 0.8
        })
    
    return ValidationResult.ambiguous(options)

def validate_director_sync(name: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Validación síncrona de directores"""
    normalized_query = normalize_input(name)
    if not normalized_query:
        return ValidationResult.not_found()
    
    # Búsqueda exacta
    exact_results = db_sync.execute_query(DIRECTOR_EXACT_SQL, (normalized_query,))
    
    if exact_results:
        if len(exact_results) == 1:
            result = exact_results[0]
            return ValidationResult.ok(result.get('id'), result.get('name'))
        
        options = []
        for result in exact_results[:5]:
            options.append({
                "id": result.get('id'),
                "name": result.get('name'),
                "score": 1.0,
                "n_titles": result.get('n_titles', 0)
            })
        return ValidationResult.ambiguous(options)
    
    # Búsqueda fuzzy
    fuzzy_results = db_sync.execute_query(DIRECTOR_FUZZY_SQL_ILIKE, (normalized_query,))
    
    if not fuzzy_results:
        return ValidationResult.not_found()
    
    if len(fuzzy_results) == 1 and not is_single_token(normalized_query):
        result = fuzzy_results[0]
        return ValidationResult.ok(result.get('id'), result.get('name'))
    
    options = []
    for result in fuzzy_results[:5]:
        options.append({
            "id": result.get('id'),
            "name": result.get('name'),
            "score": 0.8,
            "n_titles": result.get('n_titles', 0)
        })
    
    return ValidationResult.ambiguous(options)