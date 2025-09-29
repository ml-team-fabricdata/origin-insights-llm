# src/src.sql.queries/common/query_builder.py
from typing import Dict, List, Any, Optional
from .base_query import BaseQuery
from .table_constants import DatabaseSchema
from src.sql.queries.talent.specialized_queries import (
    ActorFilmographyQuery,
    DirectorFilmographyQuery,
    TalentSearchQuery
)
from src.sql.queries.content.specialized_queries import (
    ContentSearchQuery,
    MetadataQuery,
    RatingQuery
)

class QueryBuilder:
    """
    Builder class para construir queries SQL usando clases especializadas.
    Proporciona una interfaz fluida para construir queries.
    """
    
    @staticmethod
    def create_search(
        table: str,
        search_text: str,
        search_columns: List[str],
        fuzzy: bool = False,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Crea una query de búsqueda, opcionalmente fuzzy
        """
        query = ContentSearchQuery(
            table=table,
            search_columns=search_columns,
            use_fuzzy=fuzzy,
            similarity_threshold=similarity_threshold
        )
        
        return query.execute(search_text)
    
    @staticmethod
    def create_metadata(
        uid: str,
        include_hits: bool = False,
        include_availability: bool = False
    ) -> Dict[str, Any]:
        """
        Crea una query de metadata con joins opcionales
        """
        query = MetadataQuery(
            include_hits=include_hits,
            include_availability=include_availability
        )
        
        return query.execute(uid)
    
    @staticmethod
    def create_filmography(
        talent_id: str,
        talent_type: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Crea una query de filmografía para actores o directores
        """
        if talent_type == "actor":
            query = ActorFilmographyQuery(limit=limit)
        else:  # director
            query = DirectorFilmographyQuery(limit=limit)
            
        return query.execute(talent_id)
    
    @staticmethod
    def create_rating(
        uid: str,
        scope: str = "global"
    ) -> Dict[str, Any]:
        """
        Crea una query de rating/popularidad
        """
        query = RatingQuery(scope=scope)
        
        return query.execute(uid)

# Ejemplo de uso:
"""
# Búsqueda fuzzy
search_query = QueryBuilder.create_search(
    table=DatabaseSchema.METADATA.table,
    search_text="Matrix", 
    search_columns=["title", "original_title"],
    fuzzy=True
)

# Metadata con hits
metadata_query = QueryBuilder.create_metadata(
    uid="123",
    include_hits=True
)

# Filmografía de actor
filmography_query = QueryBuilder.create_filmography(
    talent_id="456",
    talent_type="actor"
)

# Rating global
rating_query = QueryBuilder.create_rating(
    uid="123",
    scope="global"
)
"""