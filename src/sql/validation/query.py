
from ..constants_sql import *

# =============================================================================
# SQL QUERIES - TITLES
# =============================================================================

EXACT_SEARCH_SQL = f"""
SELECT DISTINCT ON (m.uid)
  m.uid,
  COALESCE(m.clean_title, LOWER(m.title)) AS clean_title,
  m.year,
  m.title,
  md.type,
  md.imdb_id
FROM {AKAS_TABLE} m
LEFT JOIN {METADATA_TABLE} md ON md.uid = m.uid
WHERE LOWER(COALESCE(m.clean_title, m.title)) = LOWER(%s)
ORDER BY m.uid, m.year NULLS LAST
"""

FUZZY_SEARCH_SQL = f"""
WITH candidates AS (
  SELECT
    a.uid,
    a.title AS aka_title,
    a.year,
    GREATEST(
      {PG_TRGM_SCHEMA}.similarity(LOWER(COALESCE(a.clean_title, a.title))::text, %s::text),
      {PG_TRGM_SCHEMA}.similarity(LOWER(a.title)::text, %s::text)
    ) AS title_similarity
  FROM {AKAS_TABLE} a
  WHERE {PG_TRGM_SCHEMA}.similarity(LOWER(COALESCE(a.clean_title, a.title))::text, %s::text) >= %s
     OR {PG_TRGM_SCHEMA}.similarity(LOWER(a.title)::text, %s::text) >= %s
),
ranked AS (
  SELECT c.*, md.type, md.imdb_id
  FROM candidates c
  LEFT JOIN {METADATA_TABLE} md ON md.uid = c.uid
  WHERE c.title_similarity >= %s
)
SELECT *
FROM ranked
ORDER BY title_similarity DESC, year DESC
LIMIT %s
"""

FILMOGRAPHY_SQL = f"""
SELECT *
FROM {METADATA_TABLE} m
WHERE m.uid = %s
"""


# =============================================================================
# SQL QUERIES - ACTORS
# =============================================================================

ACTOR_EXACT_SQL = f"""
    SELECT id, name, clean_name
    FROM {CAST_TABLE}
    WHERE LOWER(name) = LOWER(%s) OR LOWER(clean_name) = LOWER(%s)
    LIMIT 1
"""

ACTOR_FUZZY_SQL_TRGM = f"""
    SELECT id, name, clean_name,
           {PG_TRGM_SCHEMA}.similarity(LOWER(name), LOWER(%s)) AS sim
    FROM {CAST_TABLE}
    WHERE LOWER(name) % LOWER(%s) OR LOWER(clean_name) % LOWER(%s)
    ORDER BY sim DESC
    LIMIT {MAX_CANDIDATES}
"""

ACTOR_FUZZY_SQL_ILIKE = f"""
    SELECT id, name, clean_name,
           0.0 AS sim
    FROM {CAST_TABLE}
    WHERE LOWER(name) LIKE CONCAT('%%', LOWER(%s), '%%')
       OR LOWER(clean_name) LIKE CONCAT('%%', LOWER(%s), '%%')
    ORDER BY name ASC
    LIMIT {MAX_CANDIDATES}
"""


# =============================================================================
# SQL QUERIES - DIRECTORS
# =============================================================================

DIRECTOR_EXACT_SQL = f"""
    SELECT d.id, d.name, d.clean_name, COALESCE(COUNT(db.uid), 0) AS n_titles
    FROM {DIRECTOR_TABLE} d
    LEFT JOIN {DIRECTED_TABLE} db ON db.director_id = d.id
    WHERE LOWER(d.name) = LOWER(%s) OR LOWER(d.clean_name) = LOWER(%s)
    GROUP BY d.id, d.name, d.clean_name
    ORDER BY n_titles DESC NULLS LAST, d.id ASC
    LIMIT 5
"""

DIRECTOR_FUZZY_SQL_TRGM = f"""
    SELECT
        d.id,
        d.name,
        d.clean_name,
        GREATEST(
            {PG_TRGM_SCHEMA}.similarity(LOWER(d.name), LOWER(%s)),
            {PG_TRGM_SCHEMA}.similarity(LOWER(d.clean_name), LOWER(%s))
        ) AS sim,
        COALESCE(COUNT(db.uid), 0) AS n_titles
    FROM {DIRECTOR_TABLE} d
    LEFT JOIN {DIRECTED_TABLE} db ON db.director_id = d.id
    WHERE
        LOWER(d.name) % LOWER(%s)
        OR LOWER(d.clean_name) % LOWER(%s)
    GROUP BY d.id, d.name, d.clean_name
    ORDER BY sim DESC, n_titles DESC, d.name ASC
    LIMIT 10;
"""

DIRECTOR_FUZZY_SQL_ILIKE = f"""
    SELECT d.id, d.name, d.clean_name,
           0.0 AS sim,
           COALESCE(COUNT(db.uid), 0) AS n_titles
    FROM {DIRECTOR_TABLE} d
    LEFT JOIN {DIRECTED_TABLE} db ON db.director_id = d.id
    WHERE LOWER(d.name) LIKE CONCAT('%%', LOWER(%s), '%%')
       OR LOWER(d.clean_name) LIKE CONCAT('%%', LOWER(%s), '%%')
    GROUP BY d.id, d.name, d.clean_name
    ORDER BY n_titles DESC, d.name ASC
    LIMIT 10
"""

