from src.sql.constants_sql import *

# =============================================================================
# OPTIMIZED SQL QUERIES - TITLES
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
WITH normalized_query AS (
  SELECT LOWER(%s::text) AS query_lower
),
candidates AS (
  SELECT
    a.uid,
    a.title AS aka_title,
    a.year,
    GREATEST(
      {PG_TRGM_SCHEMA}.similarity(LOWER(a.title), nq.query_lower)
    ) AS title_similarity
  FROM {AKAS_TABLE} a
  CROSS JOIN normalized_query nq
  WHERE (
    {PG_TRGM_SCHEMA}.similarity(LOWER(COALESCE(a.clean_title, a.title)), nq.query_lower) >= %s
    OR {PG_TRGM_SCHEMA}.similarity(LOWER(a.title), nq.query_lower) >= %s
  )
),
ranked AS (
  SELECT c.*, md.type, md.imdb_id
  FROM candidates c
  LEFT JOIN {METADATA_TABLE} md ON md.uid = c.uid
  WHERE c.title_similarity >= %s
)
SELECT *
FROM ranked
ORDER BY title_similarity DESC, year DESC NULLS LAST
LIMIT %s
"""

FILMOGRAPHY_SQL = f"""
SELECT *
FROM {METADATA_TABLE} m
WHERE m.uid = %s
"""


# =============================================================================
#  ACTORS
# =============================================================================

# FIXED: Permitir múltiples resultados exactos
ACTOR_EXACT_SQL = f"""
SELECT id, name, clean_name
FROM {CAST_TABLE}
WHERE LOWER(name) = LOWER(%s) OR LOWER(clean_name) = LOWER(%s)
ORDER BY name ASC
LIMIT {MAX_CANDIDATES}
"""


ACTOR_FUZZY_SQL_ILIKE = f"""
SELECT id, name, clean_name, 0.0 AS sim
FROM {CAST_TABLE}
WHERE LOWER(name) LIKE LOWER(CONCAT('%%', %s, '%%'))
ORDER BY 
  CASE WHEN LOWER(name) LIKE LOWER(CONCAT(%s, '%%')) THEN 1 ELSE 2 END,
  name ASC
LIMIT {MAX_CANDIDATES}
"""


# =============================================================================
# DIRECTORS
# =============================================================================

DIRECTOR_EXACT_SQL = f"""
SELECT 
  d.id, 
  d.name, 
  d.clean_name,
  (
    SELECT COUNT(*)::integer 
    FROM {DIRECTED_TABLE} db 
    WHERE db.director_id = d.id
  ) AS n_titles
FROM {DIRECTOR_TABLE} d
WHERE LOWER(d.name) = LOWER(%s) OR LOWER(d.clean_name) = LOWER(%s)
ORDER BY n_titles DESC NULLS LAST, d.name ASC
LIMIT {MAX_CANDIDATES}
"""

DIRECTOR_FUZZY_SQL_ILIKE = f"""
SELECT 
  d.id, 
  d.name, 
  d.clean_name,
  0.0 AS sim,
  (
    SELECT COUNT(*)::integer 
    FROM {DIRECTED_TABLE} db 
    WHERE db.director_id = d.id
  ) AS n_titles
FROM {DIRECTOR_TABLE} d
WHERE LOWER(d.name) LIKE LOWER(CONCAT('%%', %s, '%%'))
ORDER BY 
  CASE WHEN LOWER(d.name) LIKE LOWER(CONCAT(%s, '%%')) THEN 1 ELSE 2 END,
  n_titles DESC, 
  d.name ASC
LIMIT {MAX_CANDIDATES}
"""


