from dataclasses import dataclass
from typing import Optional, List

@dataclass
class TableInfo:
    """
    Clase que representa la información de una tabla en la base de datos
    """
    table: str
    primary_key: str
    schema: str = "public"
    search_columns: Optional[List[str]] = None
    columns: Optional[List[str]] = None
    
    def get_columns_str(self) -> str:
        """
        Retorna las columnas como string para usar en SELECT
        """
        if self.columns:
            return ", ".join(self.columns)
        return "*"

class DatabaseSchema:
    """
    Clase que centraliza la información de las tablas de la base de datos
    """
    # Tablas principales
    METADATA = TableInfo(
        table="metadata",
        primary_key="uid",
        search_columns=["title", "original_title"],
        columns=[
            "uid", "title", "type", "year", "age", "duration", "synopsis",
            "primary_genre", "genres", "primary_language", "languages",
            "primary_country", "countries", "countries_iso",
            "primary_company", "production_companies", "directors", "full_cast", "writers"
        ]
    )
    
    # Tablas de nombres alternativos
    AKAS = TableInfo(
        table="akas",
        primary_key="uid",
        search_columns=["title"]
    )
    
    # Tablas de talentos
    TALENT = TableInfo(
        table="talent",
        primary_key="cast_id",
        search_columns=["name"]
    )
    
    DIRECTORS = TableInfo(
        table="directors",
        primary_key="director_id",
        search_columns=["name"]
    )
    
    # Tablas de relaciones
    ACTED_IN = TableInfo(
        table="acted_in",
        primary_key=["cast_id", "content_id"]
    )
    
    DIRECTED = TableInfo(
        table="directed",
        primary_key=["director_id", "content_id"]
    )
    
    # Tablas de métricas
    HITS_GLOBAL = TableInfo(
        table="hits_global",
        primary_key="uid"
    )
    
    HITS_PRESENCE = TableInfo(
        table="hits_presence",
        primary_key="uid"
    )
    
    # Tablas de disponibilidad
    PRESENCE = TableInfo(
        table="presence",
        primary_key="uid",
        schema="public"
    )
    
    # Extensiones PostgreSQL
    PG_TRGM_SCHEMA = "pg_trgm"
    
    @classmethod
    def get_table_info(cls, table_name: str) -> TableInfo:
        """
        Obtiene la información de una tabla por su nombre
        """
        for attr in dir(cls):
            if not attr.startswith('_'):
                table_info = getattr(cls, attr)
                if isinstance(table_info, TableInfo) and table_info.table == table_name:
                    return table_info
        raise ValueError(f"Table {table_name} not found in schema")