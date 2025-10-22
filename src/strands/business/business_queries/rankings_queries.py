from src.strands.infrastructure.database.constants import *


QUERY_MAX_DATE = f"""
SELECT MAX(date_hits)::date AS max_date
FROM {HITS_PRESENCE_TBL}
"""

QUERY_GENRE_MOMENTUM = """
WITH base AS (
  SELECT
    COALESCE(m.primary_genre, 'Unknown') AS primary_genre,
    COALESCE(h.hits, 0)::numeric   AS hits,
    (h.date_hits::date BETWEEN %s AND %s) AS is_cur,
    (h.date_hits::date BETWEEN %s AND %s) AS is_prev
  FROM {HITS_TABLE} h
  LEFT JOIN {META_TBL} m ON m.uid = h.uid
  WHERE h.date_hits::date BETWEEN %s AND %s
    {COUNTRY_CLAUSE}
    {CT_HITS_CLAUSE}
    {CT_META_CLAUSE}
)
SELECT
  primary_genre,
  COALESCE(SUM(hits) FILTER (WHERE is_cur), 0)::numeric  AS hits_now,
  COALESCE(SUM(hits) FILTER (WHERE is_prev), 0)::numeric AS hits_prev,
  (COALESCE(SUM(hits) FILTER (WHERE is_cur), 0)::numeric
   - COALESCE(SUM(hits) FILTER (WHERE is_prev), 0)::numeric) AS delta,
  CASE WHEN COALESCE(SUM(hits) FILTER (WHERE is_prev), 0) = 0 THEN NULL
       ELSE ROUND(((COALESCE(SUM(hits) FILTER (WHERE is_cur), 0)::numeric
                    - COALESCE(SUM(hits) FILTER (WHERE is_prev), 0)::numeric)
                   / NULLIF(COALESCE(SUM(hits) FILTER (WHERE is_prev), 0)::numeric, 0))
                   * 100::numeric, 2)
  END AS pct_change
FROM base
GROUP BY primary_genre
ORDER BY delta DESC NULLS LAST, hits_now DESC NULLS LAST, primary_genre ASC
"""

# Rating/Top por UID
UID_RATING_SQL = """
SELECT
  m.uid,
  m.title,
  m.year,
  m.type,
  h.hits
FROM ms.metadata_simple_all m
LEFT JOIN ms.hits_global h ON m.uid = h.uid
WHERE m.uid = %s;
"""

# =============================================================================
# HITS / TOPS
# =============================================================================

# Top por presencia (con metadata)
QUERY_TOP_PRESENCE_WITH_METADATA = f"""
SELECT
  h.uid,
  m.title,
  m.year,
  SUM(h.hits) AS hits
FROM {HITS_PRESENCE_TBL} h
INNER JOIN {META_TBL} m ON m.uid = h.uid
{{joins_clause}}
{{where_clause}}
GROUP BY h.uid, m.title, m.year
ORDER BY hits DESC
LIMIT %s;
"""

# Top por presencia (sin metadata)
QUERY_TOP_PRESENCE_NO_METADATA = f"""
SELECT
  h.uid,
  m.title,
  m.year,
  SUM(h.hits) AS hits
FROM {HITS_PRESENCE_TBL} h
INNER JOIN {META_TBL} m ON m.uid = h.uid
{{joins_clause}}
{{where_clause}}
GROUP BY h.uid, m.title, m.year
ORDER BY hits DESC
LIMIT %s;
"""

QUERY_TOP_GLOBAL_WITH_META = f"""
SELECT
  h.uid,
  m.title,
  m.year,
  SUM(h.hits) AS hits
FROM {HITS_GLOBAL_TBL} h
INNER JOIN {META_TBL} m ON m.uid = h.uid
{{where_clause}}
GROUP BY h.uid, m.title, m.year
ORDER BY hits DESC
LIMIT %s;
"""

QUERY_TOP_GLOBAL_NO_META = f"""
SELECT
  h.uid,
  SUM(h.hits) AS hits
FROM {HITS_GLOBAL_TBL} h
INNER JOIN {META_TBL} m ON m.uid = h.uid
{{where_clause}}
GROUP BY h.uid
ORDER BY hits DESC
LIMIT %s;
"""



# Hits + calidad (global / por país)
SQL_HITS_Q_GLOBAL = """
WITH pres AS (
  SELECT platform_name, hash_unique
  FROM {PRES}
  WHERE uid = %s
  GROUP BY platform_name, hash_unique
),
filtered_prices AS (
  SELECT DISTINCT x.hash_unique
  FROM {PRICES} x
  WHERE x.hash_unique IN (SELECT hash_unique FROM pres)
  {DEF_FILTER}
  {LIC_FILTER}
)
SELECT p.platform_name,
       ARRAY_AGG(DISTINCT pr.iso_alpha2 ORDER BY pr.iso_alpha2) AS countries
FROM {PRES} pr
JOIN pres p USING (platform_name, hash_unique)
WHERE pr.hash_unique IN (SELECT hash_unique FROM filtered_prices)
GROUP BY p.platform_name
ORDER BY p.platform_name
LIMIT %s;
"""

SQL_HITS_Q_BY_COUNTRY = """
WITH pres AS (
  SELECT pr.platform_name, pr.hash_unique, pr.iso_alpha2
  FROM {PRES} pr
  WHERE pr.iso_alpha2 = %s
    AND pr.uid = %s
  GROUP BY pr.platform_name, pr.hash_unique, pr.iso_alpha2
),
filtered_prices AS (
  SELECT DISTINCT x.hash_unique
  FROM {PRICES} x
  WHERE x.hash_unique IN (SELECT hash_unique FROM pres)
  {DEF_FILTER}
  {LIC_FILTER}
)
SELECT p.platform_name,
       p.iso_alpha2 AS country
FROM pres p
JOIN filtered_prices fp USING (hash_unique)
ORDER BY p.platform_name
LIMIT %s;
"""
