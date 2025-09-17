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

# OPTIMIZED: Reducir cálculos duplicados y mejorar parámetros
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
      {PG_TRGM_SCHEMA}.similarity(LOWER(COALESCE(a.clean_title, a.title)), nq.query_lower),
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
# OPTIMIZED SQL QUERIES - ACTORS
# =============================================================================

# FIXED: Permitir múltiples resultados exactos
ACTOR_EXACT_SQL = f"""
SELECT id, name, clean_name
FROM {CAST_TABLE}
WHERE LOWER(name) = LOWER(%s) OR LOWER(clean_name) = LOWER(%s)
ORDER BY name ASC
LIMIT 10
"""

# OPTIMIZED: Mejorar cálculo de similarity
ACTOR_FUZZY_SQL_TRGM = f"""
WITH query_normalized AS (
  SELECT LOWER(%s) AS query_lower
)
SELECT 
  c.id, 
  c.name, 
  c.clean_name,
  GREATEST(
    {PG_TRGM_SCHEMA}.similarity(LOWER(c.name), qn.query_lower),
    {PG_TRGM_SCHEMA}.similarity(LOWER(COALESCE(c.clean_name, c.name)), qn.query_lower)
  ) AS sim
FROM {CAST_TABLE} c
CROSS JOIN query_normalized qn
WHERE (
  LOWER(c.name) % qn.query_lower 
  OR LOWER(COALESCE(c.clean_name, c.name)) % qn.query_lower
)
ORDER BY sim DESC, c.name ASC
LIMIT {MAX_CANDIDATES}
"""

ACTOR_FUZZY_SQL_ILIKE = f"""
SELECT id, name, clean_name, 0.0 AS sim
FROM {CAST_TABLE}
WHERE LOWER(name) LIKE LOWER(CONCAT('%%', %s, '%%'))
   OR LOWER(COALESCE(clean_name, name)) LIKE LOWER(CONCAT('%%', %s, '%%'))
ORDER BY 
  CASE WHEN LOWER(name) LIKE LOWER(CONCAT(%s, '%%')) THEN 1 ELSE 2 END,
  name ASC
LIMIT {MAX_CANDIDATES}
"""


# =============================================================================
# OPTIMIZED SQL QUERIES - DIRECTORS
# =============================================================================

# OPTIMIZED: Búsqueda exacta sin JOIN innecesario para casos simples
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
LIMIT 10
"""

# OPTIMIZED: Mejorar similarity calculation y JOIN
DIRECTOR_FUZZY_SQL_TRGM = f"""
WITH query_normalized AS (
  SELECT LOWER(%s) AS query_lower
),
director_similarities AS (
  SELECT
    d.id,
    d.name,
    d.clean_name,
    GREATEST(
      {PG_TRGM_SCHEMA}.similarity(LOWER(d.name), qn.query_lower),
      {PG_TRGM_SCHEMA}.similarity(LOWER(COALESCE(d.clean_name, d.name)), qn.query_lower)
    ) AS sim
  FROM {DIRECTOR_TABLE} d
  CROSS JOIN query_normalized qn
  WHERE (
    LOWER(d.name) % qn.query_lower
    OR LOWER(COALESCE(d.clean_name, d.name)) % qn.query_lower
  )
)
SELECT 
  ds.*,
  COALESCE(COUNT(db.uid), 0)::integer AS n_titles
FROM director_similarities ds
LEFT JOIN {DIRECTED_TABLE} db ON db.director_id = ds.id
GROUP BY ds.id, ds.name, ds.clean_name, ds.sim
ORDER BY ds.sim DESC, n_titles DESC, ds.name ASC
LIMIT 15
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
   OR LOWER(COALESCE(d.clean_name, d.name)) LIKE LOWER(CONCAT('%%', %s, '%%'))
ORDER BY 
  CASE WHEN LOWER(d.name) LIKE LOWER(CONCAT(%s, '%%')) THEN 1 ELSE 2 END,
  n_titles DESC, 
  d.name ASC
LIMIT 15
"""


# =============================================================================
# PERFORMANCE OPTIMIZED ALTERNATIVES
# =============================================================================

# Para casos donde el performance es crítico
ACTOR_EXACT_FAST_SQL = f"""
SELECT id, name, clean_name
FROM {CAST_TABLE}
WHERE name = %s OR clean_name = %s
UNION ALL
SELECT id, name, clean_name  
FROM {CAST_TABLE}
WHERE LOWER(name) = LOWER(%s) OR LOWER(clean_name) = LOWER(%s)
ORDER BY name ASC
LIMIT 10
"""

DIRECTOR_EXACT_FAST_SQL = f"""
SELECT id, name, clean_name, 0 as n_titles
FROM {DIRECTOR_TABLE}
WHERE name = %s OR clean_name = %s
UNION ALL
SELECT id, name, clean_name, 0 as n_titles
FROM {DIRECTOR_TABLE}
WHERE LOWER(name) = LOWER(%s) OR LOWER(clean_name) = LOWER(%s)
ORDER BY name ASC
LIMIT 10
"""
