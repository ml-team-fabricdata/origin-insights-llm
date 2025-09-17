from constants_sql import *

FILMOGRAPHY_SQL_ACTOR = f"""
    SELECT DISTINCT
        m.title, m.type, m.year, imdb_id
    FROM {METADATA_TABLE} m
    JOIN {ACTED_IN_TABLE} ai ON m.uid = ai.uid
    WHERE ai.cast_id = %s
    ORDER BY m.year DESC
    LIMIT %s
"""

COACTORS_SQL = f"""
    WITH actor_titles AS (
        SELECT uid
        FROM {ACTED_IN_TABLE}
        WHERE cast_id = %s
    )
    SELECT
        c2.id   AS co_actor_id,
        c2.name AS co_actor_name,
        COUNT(DISTINCT at.uid) AS films_together
    FROM actor_titles at
    JOIN {ACTED_IN_TABLE} ai2 ON ai2.uid = at.uid
    JOIN {CAST_TABLE} c2 ON c2.id = ai2.cast_id
    WHERE ai2.cast_id <> %s
    GROUP BY c2.id, c2.name
    ORDER BY films_together DESC, c2.name ASC, c2.id ASC
    LIMIT %s
"""
