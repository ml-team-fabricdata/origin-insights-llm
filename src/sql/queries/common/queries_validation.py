from src.sql.utils.constants_sql import *

# =============================================================================
# TITLES
# =============================================================================

EXACT_SEARCH_SQL = f"""
SELECT DISTINCT ON (m.uid)
  m.uid,
  m.year,
  m.title,
  md.type,
  md.imdb_id
FROM {AKAS_TABLE} m
LEFT JOIN {META_TBL} md ON md.uid = m.uid
WHERE m.title = LOWER(%s)
ORDER BY m.uid, m.year NULLS LAST
"""

FUZZY_SEARCH_SQL = f"""
SELECT {SCHEMA}.similarity(clean_title, %s::text) as title_similarity, uid, title AS aka_title, "year", directors, full_cast AS cast
FROM {AKAS_TABLE}
WHERE clean_title %% %s::text
ORDER BY title_similarity DESC
LIMIT %s;
"""

# =============================================================================
#  ACTORS
# =============================================================================

ACTOR_EXACT_SQL = f"""
SELECT id, name
FROM {CAST_TABLE}
WHERE name ILIKE %s               
ORDER BY name ASC
LIMIT {MAX_CANDIDATES}
"""

ACTOR_FUZZY_SQL_ILIKE = f"""
WITH q AS (SELECT %s::text AS s)
SELECT id, name, 0.0 AS sim
FROM {CAST_TABLE}, q
WHERE name ILIKE '%%' || q.s || '%%'
ORDER BY 
  CASE WHEN name ILIKE q.s || '%%' THEN 1 ELSE 2 END, 
  name ASC
LIMIT {MAX_CANDIDATES}
"""

# =============================================================================
# DIRECTORS
# =============================================================================

DIRECTOR_EXACT_SQL = f"""
WITH q AS (SELECT %s::text AS s)
SELECT 
  d.id, 
  d.name,
  t.n_titles
FROM {DIRECTOR_TABLE} d
CROSS JOIN q
LEFT JOIN LATERAL (
  SELECT COUNT(*)::integer AS n_titles
  FROM {DIRECTED_TABLE} db 
  WHERE db.director_id = d.id
) t ON TRUE
WHERE d.name ILIKE q.s
ORDER BY t.n_titles DESC NULLS LAST, d.name ASC
LIMIT {MAX_CANDIDATES}
"""

DIRECTOR_FUZZY_SQL_ILIKE = f"""
WITH q AS (SELECT %s::text AS s)
SELECT 
  d.id, 
  d.name, 
  0.0 AS sim,
  t.n_titles
FROM {DIRECTOR_TABLE} d
CROSS JOIN q
LEFT JOIN LATERAL (
  SELECT COUNT(*)::integer AS n_titles
  FROM {DIRECTED_TABLE} db 
  WHERE db.director_id = d.id
) t ON TRUE
WHERE d.name ILIKE '%%' || q.s || '%%'
ORDER BY 
  CASE WHEN d.name ILIKE q.s || '%%' THEN 1 ELSE 2 END,
  t.n_titles DESC NULLS LAST, 
  d.name ASC
LIMIT {MAX_CANDIDATES}
"""

