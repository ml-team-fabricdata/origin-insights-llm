from typing import Dict, Any, Optional
from src.sql.queries.common.base_query import BaseQuery
from src.sql.utils.table_constants import DatabaseSchema

class ContentSearchQuery(BaseQuery):
    """
    Clase especializada para búsqueda de contenido
    """
    def __init__(self, table: str, search_columns: list[str], use_fuzzy: bool = False, similarity_threshold: float = 0.3):
        super().__init__()
        self.table = table
        self.search_columns = search_columns
        self.use_fuzzy = use_fuzzy
        self.similarity_threshold = similarity_threshold

    def build_query(self) -> str:
        select_clause = "SELECT *"
        if self.use_fuzzy:
            similarity_terms = [
                f"similarity({col}, %s) as {col}_sim" 
                for col in self.search_columns
            ]
            select_clause = f"SELECT *, {', '.join(similarity_terms)}"
            
        where_conditions = []
        for col in self.search_columns:
            if self.use_fuzzy:
                where_conditions.append(f"similarity({col}, %s) > %s")
            else:
                where_conditions.append(f"{col} ILIKE %s")
                
        query = f"""
        {select_clause}
        FROM {self.table}
        WHERE {' OR '.join(where_conditions)}
        """
        
        if self.use_fuzzy:
            query += " ORDER BY " + ", ".join(f"{col}_sim DESC" for col in self.search_columns)
            
        return query

    def get_params(self, search_text: str) -> list:
        params = []
        if self.use_fuzzy:
            # Parámetros para el SELECT
            params.extend([search_text] * len(self.search_columns))
            # Parámetros para el WHERE
            params.extend([search_text] * len(self.search_columns))
            params.extend([self.similarity_threshold] * len(self.search_columns))
        else:
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern] * len(self.search_columns))
        return params

    def execute(self, search_text: str) -> Dict[str, Any]:
        return {
            "query": self.build_query(),
            "params": self.get_params(search_text)
        }

class MetadataQuery(BaseQuery):
    """
    Clase especializada para obtener metadata de contenido con joins opcionales
    """
    def __init__(self, include_hits: bool = False, include_availability: bool = False):
        super().__init__()
        self.include_hits = include_hits
        self.include_availability = include_availability
        
    def build_query(self) -> str:
        select_clause = "SELECT m.*"
        joins = []
        
        if self.include_hits:
            select_clause += ", h.*"
            joins.append(f"LEFT JOIN {DatabaseSchema.HITS_GLOBAL.table} h ON h.uid = m.uid")
            
        if self.include_availability:
            select_clause += ", p.*"
            joins.append(f"LEFT JOIN {DatabaseSchema.PRESENCE.table} p ON p.uid = m.uid")
            
        query = f"""
        {select_clause}
        FROM {DatabaseSchema.METADATA.table} m
        {' '.join(joins)}
        WHERE m.uid = %s
        """
        return query
        
    def execute(self, uid: str) -> Dict[str, Any]:
        return {
            "query": self.build_query(),
            "params": [uid]
        }

class RatingQuery(BaseQuery):
    """
    Clase especializada para obtener ratings/popularidad
    """
    def __init__(self, scope: str = "global"):
        super().__init__()
        self.scope = scope
        self.hits_table = (DatabaseSchema.HITS_GLOBAL.table if scope == "global" 
                          else DatabaseSchema.HITS_PRESENCE.table)
        
    def build_query(self) -> str:
        return f"""
        SELECT *
        FROM {self.hits_table}
        WHERE uid = %s
        """
        
    def execute(self, uid: str) -> Dict[str, Any]:
        return {
            "query": self.build_query(),
            "params": [uid]
        }