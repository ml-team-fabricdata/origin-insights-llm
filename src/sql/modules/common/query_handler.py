# src/sql/modules/common/query_handler.py
from typing import Dict, Any, Optional
from .query_detection import QueryDetector
from src.sql.modules.content import metadata
from src.sql.modules.business import rankings
from src.sql.modules.platform import availability

class QueryHandler:
    """
    Manejador centralizado de consultas que integra la funcionalidad
    del supervisor dentro de la estructura SQL.
    """

    def __init__(self):
        self.detector = QueryDetector()

    def handle_query(self, query: str) -> Dict[str, Any]:
        """
        Maneja una consulta de usuario y retorna la respuesta apropiada.
        Versión mejorada del handle_query del supervisor.
        """
        # Detectar tipo de consulta y lenguaje
        classification = self.detector.classify_query(query)
        lang = classification["language"]

        try:
            # Manejar consulta de popularidad
            if classification["is_popularity"]:
                return self._handle_popularity_query(query, lang)

            # Manejar consulta de metadata
            if classification["is_metadata"]:
                return self._handle_metadata_query(query, lang)

            # Manejar consulta de disponibilidad
            if classification["is_availability"]:
                return self._handle_availability_query(query, lang)

            # Manejar consulta de talento
            if classification["is_talent"]:
                return self._handle_talent_query(query, lang)

            # Fallback para consultas no reconocidas
            return self._handle_unknown_query(lang)

        except Exception as e:
            return self._handle_error(str(e), lang)

    def _handle_popularity_query(self, query: str, lang: str) -> Dict[str, Any]:
        """Maneja consultas de popularidad/hits."""
        result = rankings.process_popularity_query(query, lang)
        return {
            "ok": True,
            "type": "popularity",
            "data": result
        }

    def _handle_metadata_query(self, query: str, lang: str) -> Dict[str, Any]:
        """Maneja consultas de metadata/sinopsis."""
        result = metadata.process_metadata_query(query, lang)
        return {
            "ok": True,
            "type": "metadata",
            "data": result
        }

    def _handle_availability_query(self, query: str, lang: str) -> Dict[str, Any]:
        """Maneja consultas de disponibilidad."""
        result = availability.process_availability_query(query, lang)
        return {
            "ok": True,
            "type": "availability",
            "data": result
        }

    def _handle_talent_query(self, query: str, lang: str) -> Dict[str, Any]:
        """Maneja consultas sobre actores/directores."""
        # Implementar lógica específica para consultas de talento
        pass

    def _handle_unknown_query(self, lang: str) -> Dict[str, Any]:
        """Maneja consultas no reconocidas."""
        message = (
            "Por favor, especifica si buscas información sobre disponibilidad, "
            "popularidad, metadata o talento." if lang == "es" else
            "Please specify if you're looking for availability, "
            "popularity, metadata or talent information."
        )
        return {
            "ok": True,
            "type": "unknown",
            "data": message
        }

    def _handle_error(self, error: str, lang: str) -> Dict[str, Any]:
        """Maneja errores en el procesamiento de consultas."""
        message = (
            f"Error al procesar la consulta: {error}" if lang == "es" else
            f"Error processing query: {error}"
        )
        return {
            "ok": False,
            "type": "error",
            "data": message
        }