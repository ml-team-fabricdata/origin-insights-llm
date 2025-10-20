from typing import Dict, List, Any
from .table_constants import DatabaseSchema

# TODO: These specialized query classes don't exist yet
# from src.strands.talent.talent_queries.specialized_queries import (
#     ActorFilmographyQuery,
#     DirectorFilmographyQuery,
# )
# from src.strands.content.content_queries.specialized_queries import (
#     ContentSearchQuery,
#     MetadataQuery,
#     RatingQuery
# )

class QueryBuilder:

    @staticmethod
    def create_search(
        table: str,
        search_text: str,
        search_columns: List[str],
        fuzzy: bool = False,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
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
        if talent_type == "actor":
            query = ActorFilmographyQuery(limit=limit)
        else:
            query = DirectorFilmographyQuery(limit=limit)
        return query.execute(talent_id)

    @staticmethod
    def create_rating(
        uid: str,
        scope: str = "global"
    ) -> Dict[str, Any]:
        query = RatingQuery(scope=scope)
        return query.execute(uid)