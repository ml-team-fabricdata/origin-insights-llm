# src/src.sql.queries/common/query_templates.py
from typing import Dict, List, Any, Optional
from src.sql.utils.constants_sql import *

class QueryTemplate:
    """
    Base class for SQL query templates.
    Provides common functionality for building and formatting queries.
    """
    
    def __init__(self):
        self.params: List[Any] = []
        
    def build(self) -> str:
        """Must be implemented by child classes"""
        raise NotImplementedError
    
    def get_params(self) -> List[Any]:
        """Returns the parameters collected during query building"""
        return self.params

class SearchTemplate(QueryTemplate):
    """Template for search queries with optional fuzzy matching"""
    
    def __init__(
        self,
        table: str,
        search_columns: List[str],
        return_columns: Optional[List[str]] = None,
        use_fuzzy: bool = False,
        order_by: Optional[List[str]] = None
    ):
        super().__init__()
        self.table = table
        self.search_columns = search_columns
        self.return_columns = return_columns or ['*']
        self.use_fuzzy = use_fuzzy
        self.order_by = order_by or []
        
    def build(self) -> str:
        columns = ", ".join(self.return_columns)
        
        if self.use_fuzzy:
            search_conditions = []
            for col in self.search_columns:
                search_conditions.append(
                    f"{PG_TRGM_SCHEMA}.similarity(LOWER({col}), LOWER(%s)) >= %s"
                )
            where_clause = " OR ".join(search_conditions)
        else:
            search_conditions = [f"LOWER({col}) = LOWER(%s)" for col in self.search_columns]
            where_clause = " OR ".join(search_conditions)
            
        order_clause = (
            f"ORDER BY {', '.join(self.order_by)}" if self.order_by 
            else ""
        )
        
        return f"""
        SELECT {columns}
        FROM {self.table}
        WHERE {where_clause}
        {order_clause}
        """

class MetadataTemplate(QueryTemplate):
    """Template for metadata queries with optional joins"""
    
    def __init__(
        self,
        base_table: str = METADATA_TABLE,
        joins: Optional[Dict[str, str]] = None,
        conditions: Optional[Dict[str, str]] = None
    ):
        super().__init__()
        self.base_table = base_table
        self.joins = joins or {}
        self.conditions = conditions or {}
        
    def build(self) -> str:
        join_clauses = []
        for table, condition in self.joins.items():
            join_clauses.append(f"LEFT JOIN {table} ON {condition}")
            
        where_conditions = []
        for column, operator in self.conditions.items():
            where_conditions.append(f"{column} {operator} %s")
            
        joins_sql = " ".join(join_clauses)
        where_sql = (
            f"WHERE {' AND '.join(where_conditions)}" 
            if where_conditions else ""
        )
        
        return f"""
        SELECT DISTINCT ON (m.uid)
            m.*
        FROM {self.base_table} m
        {joins_sql}
        {where_sql}
        """

class FilmographyTemplate(QueryTemplate):
    """Template for filmography queries (actors/directors)"""
    
    def __init__(
        self,
        talent_table: str,
        id_column: str,
        include_metadata: bool = True,
        order_by: Optional[List[str]] = None
    ):
        super().__init__()
        self.talent_table = talent_table
        self.id_column = id_column
        self.include_metadata = include_metadata
        self.order_by = order_by or ["m.year DESC NULLS LAST", "m.title"]
        
    def build(self) -> str:
        metadata_join = f"""
        INNER JOIN {METADATA_TABLE} m ON t.uid = m.uid
        """ if self.include_metadata else ""
        
        metadata_columns = """
            m.title,
            m.type,
            m.year,
            m.imdb_id,
        """ if self.include_metadata else "t.*"
        
        order_clause = f"ORDER BY {', '.join(self.order_by)}"
        
        return f"""
        SELECT DISTINCT
            {metadata_columns}
        FROM {self.talent_table} t
        {metadata_join}
        WHERE t.{self.id_column} = %s
        {order_clause}
        """

class RatingTemplate(QueryTemplate):
    """Template for rating and popularity queries"""
    
    def __init__(
        self,
        hits_table: str,
        group_by: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None
    ):
        super().__init__()
        self.hits_table = hits_table
        self.group_by = group_by or ["m.uid", "m.title", "m.year", "m.type"]
        self.metrics = metrics or [
            "SUM(h.hits) AS total_hits",
            "AVG(h.hits) AS avg_hits",
            "COUNT(h.hits) AS hit_count"
        ]
        
    def build(self) -> str:
        metrics_sql = ",\n            ".join(self.metrics)
        group_by_sql = ", ".join(self.group_by)
        
        return f"""
        SELECT
            {", ".join(self.group_by)},
            {metrics_sql}
        FROM {METADATA_TABLE} m
        LEFT JOIN {self.hits_table} h ON m.uid = h.uid
        WHERE m.uid = %s
        GROUP BY {group_by_sql}
        """

# Ejemplo de uso:
"""
# Búsqueda fuzzy de títulos
search = SearchTemplate(
    table=METADATA_TABLE,
    search_columns=['title', 'original_title'],
    use_fuzzy=True,
    order_by=['similarity DESC']
)

# Filmografía de actor
filmography = FilmographyTemplate(
    talent_table=ACTED_IN_TABLE,
    id_column='cast_id'
)

# Rating global
rating = RatingTemplate(
    hits_table=HITS_GLOBAL_TBL
)
"""