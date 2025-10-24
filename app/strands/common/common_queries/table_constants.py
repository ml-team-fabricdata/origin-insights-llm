from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TableInfo:
    """Información detallada sobre una tabla"""
    name: str
    schema: str
    primary_key: str
    columns: List[str]
    
    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"

class DatabaseSchema:
    """Centraliza toda la información sobre las tablas de la base de datos"""
    
    METADATA = TableInfo(
        name="new_cp_metadata_estandar",
        schema="ms",
        primary_key="uid",
        columns=[
            "uid", "title", "original_title", "year", "type",
            "synopsis", "imdb_id", "directors", "full_cast"
        ]
    )
    
    HITS_GLOBAL = TableInfo(
        name="hits_global",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "uid", "hits", "date_hits", "year",
            "content_type", "imdb_id"
        ]
    )
    
    HITS_PRESENCE = TableInfo(
        name="hits_presence_2",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "uid", "hits", "country", "date_hits",
            "content_type", "year"
        ]
    )
    
    PRESENCE = TableInfo(
        name="new_cp_presence",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "uid", "platform_name", "platform_country",
            "iso_alpha2", "in_on", "out_on"
        ]
    )
    
    ACTORS = TableInfo(
        name="cast",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "name", "role", "order_"
        ]
    )
    
    DIRECTORS = TableInfo(
        name="directors",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "name"
        ]
    )
    
    ACTED_IN = TableInfo(
        name="acted_in",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "uid", "cast_id"
        ]
    )
    
    DIRECTED = TableInfo(
        name="directed",
        schema="ms",
        primary_key="id",
        columns=[
            "id", "uid", "director_id"
        ]
    )

    @classmethod
    def get_table(cls, table_name: str) -> TableInfo:
        """Obtiene la información de una tabla por su nombre"""
        return getattr(cls, table_name.upper(), None)