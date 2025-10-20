from src.strands.utils.constants_sql import *

FILMOGRAPHY_SQL_DIRECTOR = f"""
    SELECT DISTINCT
        m.uid,
        m.title, 
        m.type, 
        m.year, 
        m.imdb_id
    FROM {META_TBL} m
    INNER JOIN {DIRECTED_TABLE} dt ON m.uid = dt.uid
    WHERE dt.director_id = %s
    ORDER BY m.year DESC NULLS LAST, m.title
    LIMIT %s
"""

CODIRECTORS_SQL = f"""
    WITH director_films AS (
        SELECT uid
        FROM {DIRECTED_TABLE}
        WHERE director_id = %s
    )
    SELECT
        d.id AS co_director_id,
        d.name AS co_director_name,
        COUNT(DISTINCT df.uid) AS shared_titles
    FROM director_films df
    INNER JOIN {DIRECTED_TABLE} dt ON df.uid = dt.uid
    INNER JOIN {DIRECTOR_TABLE} d ON d.id = dt.director_id
    WHERE dt.director_id != %s
    GROUP BY d.id, d.name
    HAVING COUNT(DISTINCT df.uid) > 0
    ORDER BY shared_titles DESC, d.name
    LIMIT %s
"""
