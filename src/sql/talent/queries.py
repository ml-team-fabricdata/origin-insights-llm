from src.sql.constants_sql import *


# =============================================================================
# ACTORS
# =============================================================================


FILMOGRAPHY_SQL_ACTOR = f"""
    SELECT 
        m.title,
        m.type,
        m.year,
        m.imdb_id
    FROM {ACTED_IN_TABLE} ai
    INNER JOIN {METADATA_TABLE} m ON ai.uid = m.uid
    WHERE ai.cast_id = $1
    ORDER BY m.year DESC NULLS LAST, m.title
    LIMIT $2
"""

COACTORS_SQL = f"""
    WITH actor_films AS (
        SELECT uid 
        FROM {ACTED_IN_TABLE} 
        WHERE cast_id = $1
    )
    SELECT 
        c.id AS co_actor_id,
        c.name AS co_actor_name,
        COUNT(*) AS films_together
    FROM actor_films af
    INNER JOIN {ACTED_IN_TABLE} ai ON af.uid = ai.uid
    INNER JOIN {CAST_TABLE} c ON ai.cast_id = c.id
    WHERE ai.cast_id != $2
    GROUP BY c.id, c.name
    HAVING COUNT(*) > 1
    ORDER BY films_together DESC, c.name, c.id
    LIMIT $3
"""

# =============================================================================
# DIRECTORS
# =============================================================================


FILMOGRAPHY_SQL_DIRECTOR = f"""
    SELECT DISTINCT
        m.title, m.type, m.year, m.imdb_id
    FROM {METADATA_TABLE} m
    JOIN {DIRECTED_TABLE} db ON m.uid = db.uid
    WHERE db.director_id = %s
    ORDER BY m.year DESC
    LIMIT %s
"""

CODIRECTORS_SQL = f"""
    SELECT
        d2.id   AS co_director_id,
        d2.name AS co_director_name,
        COUNT(DISTINCT db1.uid) AS shared_titles
    FROM {DIRECTED_TABLE} db1
    JOIN {DIRECTED_TABLE} db2 ON db1.uid = db2.uid AND db2.director_id <> db1.director_id
    JOIN {DIRECTOR_TABLE} d2 ON d2.id = db2.director_id
    WHERE db1.director_id = %s
    GROUP BY d2.id, d2.name
    ORDER BY shared_titles DESC
    LIMIT %s
"""


# =============================================================================
# COLLABORATIONS
# =============================================================================


COMMON_TITLES_ACTOR_DIRECTOR_SQL = f"""
    SELECT DISTINCT
        m.title, m.type, m.year, m.imdb_id
    FROM {METADATA_TABLE} m
    JOIN {ACTED_IN_TABLE} ai ON m.uid = ai.uid
    JOIN {DIRECTED_TABLE} db ON m.uid = db.uid
    WHERE ai.cast_id = %s
      AND db.director_id = %s
    ORDER BY m.year DESC
    LIMIT %s
"""
