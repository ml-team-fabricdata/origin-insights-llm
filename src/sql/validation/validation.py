from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List, Optional, Union

from src.sql_db import db
from query import *

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _clean_text(text: str) -> str:
    """Clean and normalize text for search."""
    if not text:
        return ""
    
    normalized = unicodedata.normalize("NFKD", text).lower()
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _normalize_input(input_data: Union[str, List[str], Any]) -> str:
    """Normalize input, handling different input types."""
    if not input_data:
        return ""
    
    if isinstance(input_data, list):
        if len(input_data) > 0:
            input_data = input_data[0]
        else:
            return ""
    
    return str(input_data).strip() if input_data else ""


def _is_single_token(text: str) -> bool:
    """Check if text is a single word/token."""
    if not text or not isinstance(text, str):
        return False
    return len(text.strip().split()) == 1


def _normalize_threshold(threshold: Optional[float] = None) -> float:
    """Normalize validation threshold."""
    if threshold is None:
        return FUZZY_THRESHOLD
    try:
        return max(0.1, min(1.0, float(threshold)))
    except (ValueError, TypeError):
        return FUZZY_THRESHOLD


# =============================================================================
# WORKING VALIDATION FUNCTIONS (SIMPLIFIED)
# =============================================================================

def validate_title(title: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Title validation using optimized queries."""
    query_text = _normalize_input(title)
    if not query_text:
        return {"status": "not_found"}
    
    normalized_title = _clean_text(query_text)
    if not normalized_title:
        return {"status": "not_found"}
    
    logger.debug(f"Validating title: '{query_text}' (normalized: '{normalized_title}')")
    
    # 1. EXACT SEARCH
    try:
        exact_results = db.execute_query(EXACT_SEARCH_SQL, (normalized_title,))
        
        if exact_results:
            if len(exact_results) == 1:
                row = exact_results[0]
                return {
                    "status": "resolved",
                    "result": {
                        "uid": row.get('uid'),
                        "title": row.get('title'),
                        "aka_title": row.get('title'),
                        "imdb_id": row.get('imdb_id'),
                        "year": row.get('year'),
                        "type": row.get('type'),
                        "title_similarity": 1.0
                    }
                }
            
            # Multiple exact results - ambiguous
            options = []
            for row in exact_results[:8]:
                options.append({
                    "uid": row.get('uid'),
                    "title": row.get('title'),
                    "year": row.get('year'),
                    "type": row.get('type'),
                    "imdb_id": row.get('imdb_id')
                })
            
            return {"status": "ambiguous", "options": options}
    
    except Exception as e:
        logger.error(f"Error in title exact search: {e}")
    
    # 2. FUZZY SEARCH with fallbacks
    threshold = _normalize_threshold(threshold)
    fallback_thresholds = [threshold, 0.3, 0.2]
    
    for current_threshold in fallback_thresholds:
        logger.debug(f"Trying title fuzzy search with threshold {current_threshold}")
        
        try:
            params = (normalized_title, current_threshold, current_threshold, DEFAULT_FUZZY_LIMIT)
            fuzzy_results = db.execute_query(FUZZY_SEARCH_SQL, params)
            
            if fuzzy_results:
                # Apply single token rule
                is_single_token = _is_single_token(query_text)
                
                if len(fuzzy_results) == 1 and not is_single_token:
                    row = fuzzy_results[0]
                    similarity = float(row.get('title_similarity', 0) or 0)
                    
                    if similarity >= current_threshold:
                        return {
                            "status": "resolved",
                            "result": {
                                "uid": row.get('uid'),
                                "title": row.get('aka_title'),
                                "aka_title": row.get('aka_title'),
                                "imdb_id": row.get('imdb_id'),
                                "year": row.get('year'),
                                "type": row.get('type'),
                                "title_similarity": similarity
                            }
                        }
                
                # Multiple results or single token - ambiguous
                options = []
                for row in fuzzy_results[:8]:
                    options.append({
                        "uid": row.get('uid'),
                        "title": row.get('aka_title'),
                        "year": row.get('year'),
                        "type": row.get('type'),
                        "imdb_id": row.get('imdb_id'),
                        "title_similarity": float(row.get('title_similarity', 0) or 0)
                    })
                
                return {"status": "ambiguous", "options": options}
        
        except Exception as e:
            logger.error(f"Error in title fuzzy search with threshold {current_threshold}: {e}")
            continue
    
    return {"status": "not_found"}


def validate_actor(name: Union[str, List[str], Any], threshold: Optional[float] = None) -> Dict[str, Any]:
    """Actor validation with working fuzzy search."""
    query_text = _normalize_input(name)
    if not query_text:
        return {"status": "not_found"}
    
    threshold = _normalize_threshold(threshold)
    
    logger.debug(f"Validating actor: '{query_text}' with threshold {threshold}")
    
    # 1. EXACT SEARCH
    try:
        exact_results = db.execute_query(ACTOR_EXACT_SQL, (query_text, query_text))
        
        if exact_results:
            if len(exact_results) == 1:
                row = exact_results[0]
                return {
                    "status": "ok",
                    "id": row.get('id'),
                    "name": row.get('name')
                }
            
            # Multiple exact results - ambiguous
            options = []
            for row in exact_results[:5]:
                options.append({
                    "id": row.get('id'),
                    "name": row.get('name'),
                    "score": 1.0
                })
            
            return {"status": "ambiguous", "options": options}
    
    except Exception as e:
        logger.error(f"Error in actor exact search: {e}")
    
    # 2. WORKING FUZZY SEARCH (simplified to avoid the problematic query)
    fallback_thresholds = [threshold, 0.3, 0.2]
    
    for current_threshold in fallback_thresholds:
        logger.debug(f"Trying actor fuzzy search with threshold {current_threshold}")
        
        try:
            # Use ILIKE fallback which should work
            fuzzy_results = db.execute_query(ACTOR_FUZZY_SQL_ILIKE, (query_text, query_text))
            
            if fuzzy_results:
                # Filter by manual similarity check (since ILIKE doesn't provide similarity scores)
                valid_results = []
                
                # Simple similarity: if the name contains the query
                for row in fuzzy_results:
                    name = row.get('name', '').lower()
                    clean_name = row.get('clean_name', '').lower()
                    query_lower = query_text.lower()
                    
                    # Simple scoring: exact match = 1.0, contains at start = 0.8, contains = 0.5
                    if name == query_lower or clean_name == query_lower:
                        score = 1.0
                    elif name.startswith(query_lower) or clean_name.startswith(query_lower):
                        score = 0.8
                    elif query_lower in name or query_lower in clean_name:
                        score = 0.5
                    else:
                        score = 0.3
                    
                    if score >= current_threshold:
                        row_copy = dict(row)
                        row_copy['sim'] = score
                        valid_results.append(row_copy)
                
                if not valid_results:
                    continue
                
                # Sort by score
                valid_results.sort(key=lambda x: x['sim'], reverse=True)
                
                # Apply single token rule
                is_single_token = _is_single_token(query_text)
                
                if len(valid_results) == 1 and not is_single_token:
                    row = valid_results[0]
                    return {
                        "status": "ok",
                        "id": row.get('id'),
                        "name": row.get('name')
                    }
                
                # Multiple results or single token - ambiguous
                options = []
                for row in valid_results[:5]:
                    options.append({
                        "id": row.get('id'),
                        "name": row.get('name'),
                        "score": float(row.get('sim', 0))
                    })
                
                return {"status": "ambiguous", "options": options}
        
        except Exception as e:
            logger.error(f"Error in actor fuzzy search with threshold {current_threshold}: {e}")
            continue
    
    return {"status": "not_found"}


def validate_director(name: Union[str, List[str], Any], threshold: Optional[float] = None) -> Dict[str, Any]:
    """Director validation with working fuzzy search."""
    query_text = _normalize_input(name)
    if not query_text:
        return {"status": "not_found"}
    
    threshold = _normalize_threshold(threshold)
    
    logger.debug(f"Validating director: '{query_text}' with threshold {threshold}")
    
    # 1. EXACT SEARCH
    try:
        exact_results = db.execute_query(DIRECTOR_EXACT_SQL, (query_text, query_text))
        
        if exact_results:
            if len(exact_results) == 1:
                row = exact_results[0]
                return {
                    "status": "ok",
                    "id": row.get('id'),
                    "name": row.get('name')
                }
            
            # Multiple exact results - ambiguous
            options = []
            for row in exact_results[:5]:
                options.append({
                    "id": row.get('id'),
                    "name": row.get('name'),
                    "score": float(row.get('n_titles', 0) or 0)
                })
            
            return {"status": "ambiguous", "options": options}
    
    except Exception as e:
        logger.error(f"Error in director exact search: {e}")
    
    # 2. WORKING FUZZY SEARCH (simplified to avoid the problematic query)
    fallback_thresholds = [threshold, 0.3, 0.2]
    
    for current_threshold in fallback_thresholds:
        logger.debug(f"Trying director fuzzy search with threshold {current_threshold}")
        
        try:
            # Use ILIKE fallback which should work
            fuzzy_results = db.execute_query(DIRECTOR_FUZZY_SQL_ILIKE, (query_text, query_text))
            
            if fuzzy_results:
                # Filter by manual similarity check
                valid_results = []
                
                for row in fuzzy_results:
                    name = row.get('name', '').lower()
                    clean_name = row.get('clean_name', '').lower()
                    query_lower = query_text.lower()
                    
                    # Simple scoring
                    if name == query_lower or clean_name == query_lower:
                        score = 1.0
                    elif name.startswith(query_lower) or clean_name.startswith(query_lower):
                        score = 0.8
                    elif query_lower in name or query_lower in clean_name:
                        score = 0.5
                    else:
                        score = 0.3
                    
                    if score >= current_threshold:
                        row_copy = dict(row)
                        row_copy['sim'] = score
                        valid_results.append(row_copy)
                
                if not valid_results:
                    continue
                
                # Sort by score, then by n_titles
                valid_results.sort(key=lambda x: (x['sim'], x.get('n_titles', 0)), reverse=True)
                
                # Apply single token rule
                is_single_token = _is_single_token(query_text)
                
                if len(valid_results) == 1 and not is_single_token:
                    row = valid_results[0]
                    return {
                        "status": "ok",
                        "id": row.get('id'),
                        "name": row.get('name')
                    }
                
                # Multiple results or single token - ambiguous
                options = []
                for row in valid_results[:5]:
                    options.append({
                        "id": row.get('id'),
                        "name": row.get('name'),
                        "score": float(row.get('sim', 0)),
                        "n_titles": int(row.get('n_titles', 0) or 0)
                    })
                
                return {"status": "ambiguous", "options": options}
        
        except Exception as e:
            logger.error(f"Error in director fuzzy search with threshold {current_threshold}: {e}")
            continue
    
    return {"status": "not_found"}


# =============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# =============================================================================

def search_title_exact(title: str) -> List[Dict[str, Any]]:
    """Exact title search (for backward compatibility)."""
    if not title:
        return []
    
    normalized_title = _clean_text(title)
    if not normalized_title:
        return []
    
    try:
        results = db.execute_query(EXACT_SEARCH_SQL, (normalized_title,))
        return results or []
    except Exception as e:
        logger.error(f"Error in exact search: {e}")
        return []


def search_title_fuzzy(
    title: str,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int = DEFAULT_FUZZY_LIMIT
) -> List[Dict[str, Any]]:
    """Fuzzy title search (for backward compatibility)."""
    if not title:
        return []
    
    normalized_title = _clean_text(title)
    if not normalized_title:
        return []
    
    try:
        params = (normalized_title, threshold, threshold, threshold, limit)
        results = db.execute_query(FUZZY_SEARCH_SQL, params)
        return results or []
        
    except Exception as e:
        logger.error(f"Error in fuzzy search: {e}")
        return []


def search_title(
    title: str,
    *,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int = DEFAULT_FUZZY_LIMIT
) -> Dict[str, Any]:
    """Main title search (for backward compatibility)."""
    return validate_title(title, threshold)