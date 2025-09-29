# src/sql/modules/common/query_detection.py
from typing import Dict, Tuple, Optional, Any, List
from src.sql.tools.all_tools import ALL_SQL_TOOLS
from src.sql.utils.validators_shared import normalize_text

# Importar las herramientas específicas
from src.sql.tools.business.rankings_tools import RANKING_TOOLS
from src.sql.tools.content.metadata_tools import METADATA_TOOLS
from src.sql.tools.platform.availability_tools import AVAILABILITY_TOOLS
from src.sql.tools.talent.actors_tools import ACTOR_TOOLS
from src.sql.tools.talent.directors_tools import DIRECTOR_TOOLS

class QueryDetector:
    """
    Clase para detección y clasificación de consultas de usuario.
    Basado en las funciones del supervisor pero integrado en la estructura SQL.
    """
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detecta el idioma del texto basado en palabras clave."""
        text = (text or "").lower()
        es_keywords = [
            "dónde", "donde", "película", "pelicula", 
            "serie", "sinopsis", "popularidad", "hits"
        ]
        return "es" if any(kw in text for kw in es_keywords) else "en"

    @staticmethod
    def is_popularity_query(text: str) -> bool:
        """Detecta si la consulta es sobre popularidad/hits."""
        text = normalize_text(text)
        popularity_keywords = [
            "hits", "popularidad", "top ", " ranking", 
            "más popular", "most popular"
        ]
        return any(kw in text for kw in popularity_keywords)

    @staticmethod
    def is_metadata_query(text: str) -> bool:
        """Detecta si la consulta es sobre metadata/sinopsis."""
        text = normalize_text(text)
        metadata_keywords = [
            "sinopsis", "de qué trata", "de que trata", 
            "plot", "synopsis"
        ]
        return any(kw in text for kw in metadata_keywords)
    
    @staticmethod
    def is_talent_query(text: str) -> bool:
        """Detecta si la consulta es sobre actores o directores."""
        text = normalize_text(text)
        talent_keywords = [
            "actor", "actriz", "director", "directora",
            "actúa", "actua", "dirigió", "dirigio"
        ]
        return any(kw in text for kw in talent_keywords)

    @staticmethod
    def is_availability_query(text: str) -> bool:
        """Detecta si la consulta es sobre disponibilidad."""
        text = normalize_text(text)
        availability_keywords = [
            "disponible", "available", "donde ver", 
            "where to watch", "plataforma", "platform"
        ]
        return any(kw in text for kw in availability_keywords)

    @staticmethod
    def detect_talent_type(text: str) -> Optional[str]:
        """Detecta si la consulta es específicamente sobre actores o directores."""
        text = normalize_text(text)
        actor_keywords = ["actor", "actriz", "actúa", "actua", "actuó", "actuo"]
        director_keywords = ["director", "directora", "dirigió", "dirigio", "dirige"]
        
        is_actor = any(kw in text for kw in actor_keywords)
        is_director = any(kw in text for kw in director_keywords)
        
        if is_actor and not is_director:
            return "actor"
        elif is_director and not is_actor:
            return "director"
        return None

    @classmethod
    def classify_query(cls, query: str) -> Dict[str, Any]:
        """
        Clasifica el tipo de consulta y retorna un diccionario con los tipos detectados
        y las herramientas aplicables.
        """
        # Detectar tipo principal
        query_types = {
            "popularity": cls.is_popularity_query(query),
            "metadata": cls.is_metadata_query(query),
            "talent": cls.is_talent_query(query),
            "availability": cls.is_availability_query(query)
        }
        
        # Obtener el tipo principal (el primero que sea True)
        main_type = next((k for k, v in query_types.items() if v), None)
        
        # Detectar subtipo para consultas de talento
        sub_type = cls.detect_talent_type(query) if main_type == "talent" else None
        
        # Obtener herramientas aplicables
        applicable_tools = get_query_tools(main_type, sub_type) if main_type else []
        
        return {
            "query_types": query_types,
            "main_type": main_type,
            "sub_type": sub_type,
            "language": cls.detect_language(query),
            "applicable_tools": applicable_tools
        }

def get_query_tools(query_type: str, sub_type: Optional[str] = None) -> list:
    """
    Factory para obtener las herramientas apropiadas según el tipo de consulta.
    
    Args:
        query_type: Tipo principal de la consulta (popularity, metadata, etc.)
        sub_type: Subtipo específico (actor, director, etc. para talent)
    
    Returns:
        Lista de herramientas aplicables para el tipo de consulta
    """
    tools_map = {
        "popularity": RANKING_TOOLS,
        "metadata": METADATA_TOOLS,
        "availability": AVAILABILITY_TOOLS,
        "talent": {
            "actor": ACTOR_TOOLS,
            "director": DIRECTOR_TOOLS,
            None: ACTOR_TOOLS + DIRECTOR_TOOLS  # Si no se especifica subtipo
        }
    }
    
    if query_type == "talent" and sub_type:
        return tools_map[query_type].get(sub_type, [])
    
    return tools_map.get(query_type, [])