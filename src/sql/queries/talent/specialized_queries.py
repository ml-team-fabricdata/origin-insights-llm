# src/src.sql.queries/talent/specialized_queries.py
from typing import List, Any, Optional
from src.sql.queries.common.base_query import BaseJoinQuery, BaseSearchQuery
from src.sql.queries.common.table_constants import DatabaseSchema

class ActorFilmographyQuery(BaseJoinQuery):
    """Query especializada para obtener la filmografía de un actor"""
    
    def __init__(self, actor_id: str, include_metadata: bool = True):
        self.actor_id = actor_id
        self.include_metadata = include_metadata
        
        main_table = DatabaseSchema.ACTED_IN
        joins = {
            DatabaseSchema.METADATA: "m.uid = ai.uid",
            DatabaseSchema.ACTORS: "c.id = ai.cast_id"
        }
        
        super().__init__(main_table, joins)
        self.params = [actor_id]
    
    def _build_select_clause(self) -> str:
        if self.include_metadata:
            return """
                m.title,
                m.type,
                m.year,
                m.imdb_id,
                c.name as actor_name,
                c.role
            """
        return "ai.*"
    
    def _build_where_clause(self) -> str:
        return "WHERE ai.cast_id = %s"
    
    def _build_order_clause(self) -> str:
        return "ORDER BY m.year DESC NULLS LAST, m.title"

class DirectorFilmographyQuery(BaseJoinQuery):
    """Query especializada para obtener la filmografía de un director"""
    
    def __init__(self, director_id: str):
        self.director_id = director_id
        
        main_table = DatabaseSchema.DIRECTED
        joins = {
            DatabaseSchema.METADATA: "m.uid = d.uid",
            DatabaseSchema.DIRECTORS: "dir.id = d.director_id"
        }
        
        super().__init__(main_table, joins)
        self.params = [director_id]
    
    def _build_select_clause(self) -> str:
        return """
            m.title,
            m.type,
            m.year,
            m.imdb_id,
            dir.name as director_name
        """
    
    def _build_where_clause(self) -> str:
        return "WHERE d.director_id = %s"
    
    def _build_order_clause(self) -> str:
        return "ORDER BY m.year DESC NULLS LAST, m.title"

class TalentSearchQuery(BaseSearchQuery):
    """Query especializada para búsqueda de talentos (actores/directores)"""
    
    def __init__(
        self,
        search_text: str,
        talent_type: str = "actor",
        use_fuzzy: bool = True,
        similarity_threshold: float = 0.3
    ):
        self.search_text = search_text
        self.similarity_threshold = similarity_threshold
        
        table = (
            DatabaseSchema.ACTORS if talent_type == "actor"
            else DatabaseSchema.DIRECTORS
        )
        
        super().__init__(
            table=table,
            search_columns=["name"],
            return_columns=["id", "name"],
            use_fuzzy=use_fuzzy
        )
        
        self.params = [search_text]
        if use_fuzzy:
            self.params.append(similarity_threshold)
    
    def _build_where_clause(self) -> str:
        if self.use_fuzzy:
            return "WHERE similarity(LOWER(name), LOWER(%s)) >= %s"
        return "WHERE LOWER(name) = LOWER(%s)"
    
    def _build_order_clause(self) -> str:
        if self.use_fuzzy:
            return "ORDER BY similarity(LOWER(name), LOWER(%s)) DESC"
        return "ORDER BY name"