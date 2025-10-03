from src.sql.utils.constants_sql import *

FILMOGRAPHY_SQL_ACTOR = f"""
    SELECT
        m.title,
        m.type,
        m.year,
        m.imdb_id
    FROM {ACTED_IN_TABLE} ai
    INNER JOIN {METADATA_TABLE} m ON ai.uid = m.uid
    WHERE ai.cast_id = %s
    ORDER BY m.year DESC NULLS LAST, m.title
    LIMIT %s
"""

COACTORS_SQL = f"""
    WITH actor_films AS (
        SELECT uid
        FROM {ACTED_IN_TABLE}
        WHERE cast_id = %s
    )
    SELECT
        c.id AS co_actor_id,
        c.name AS co_actor_name,
        COUNT(DISTINCT af.uid) AS films_together
    FROM actor_films af
    INNER JOIN {ACTED_IN_TABLE} ai ON af.uid = ai.uid
    INNER JOIN {CAST_TABLE} c ON ai.cast_id = c.id
    WHERE ai.cast_id != %s
    GROUP BY c.id, c.name
    HAVING COUNT(DISTINCT af.uid) > 1
    ORDER BY films_together DESC, c.name, c.id
    LIMIT %s
"""
