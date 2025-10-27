from src.strands.infrastructure.database.constants import *

PLATFORM_FILTER = "p.platform_name ILIKE %(platform)s" 

SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY_PERCENTAGE = f"""
WITH stats AS (
  SELECT 
    COUNT(CASE WHEN is_exclusive = 'Yes' THEN 1 END) AS exclusive_count,
    COUNT(DISTINCT uid) AS total_on_platform
  FROM {PRES_TBL}
  WHERE platform_name ILIKE %s
    AND iso_alpha2 = %s
    AND out_on IS NULL
),
exclusive_titles AS (
  SELECT 
    p.uid,
    m.title,
    m.type,
    m.year
  FROM {PRES_TBL} p
  JOIN {META_TBL} m ON m.uid = p.uid
  WHERE p.platform_name ILIKE %s
    AND p.iso_alpha2 = %s
    AND p.out_on IS NULL
    AND p.is_exclusive = 'Yes'
  ORDER BY m.year DESC NULLS LAST, m.title ASC
  LIMIT %s
)
SELECT 
  e.uid,
  e.title,
  e.type,
  e.year,
  s.exclusive_count::int AS exclusive_titles,
  s.total_on_platform::int AS total_titles_on_platform,
  ROUND(s.exclusive_count * 100.0 / NULLIF(s.total_on_platform, 0), 2) AS exclusivity_pct
FROM exclusive_titles e
CROSS JOIN stats s;
"""

SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY_PCT = f"""
WITH base AS (
  SELECT DISTINCT p.uid
  FROM {PRES_TBL} p
  WHERE {PLATFORM_FILTER}
    AND p.iso_alpha2 = %(country)s
    AND p.out_on IS NULL
),
exclusive AS (
  SELECT DISTINCT p.uid
  FROM {PRES_TBL} p
  WHERE {PLATFORM_FILTER}
    AND p.iso_alpha2 = %(country)s
    AND p.out_on IS NULL
    AND p.is_exclusive = 'Yes'
),
stats AS (
  SELECT 
    (SELECT COUNT(*) FROM exclusive) AS exclusive_count,
    (SELECT COUNT(*) FROM base)      AS total_on_platform
),
exclusive_titles AS (
  SELECT e.uid, m.title, m.type, m.year
  FROM exclusive e
  JOIN {META_TBL} m ON m.uid = e.uid
  ORDER BY m.year DESC NULLS LAST, m.title ASC
  LIMIT %(limit)s
)
SELECT 
  et.uid,
  et.title,
  et.type,
  et.year,
  s.exclusive_count::int AS exclusive_titles,
  s.total_on_platform::int AS total_titles_on_platform,
  ROUND(s.exclusive_count * 100.0 / NULLIF(s.total_on_platform, 0), 2) AS exclusivity_pct
FROM exclusive_titles et
CROSS JOIN stats s;
"""


SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY = f"""
SELECT DISTINCT ON (p.uid)
  m.uid, m.title, m.type, m.year
FROM {PRES_TBL} p
JOIN {META_TBL} m ON m.uid = p.uid
WHERE {PLATFORM_FILTER}
  AND p.iso_alpha2 = %(country)s
  AND p.out_on IS NULL
  AND p.is_exclusive = 'Yes'
ORDER BY p.uid, m.year DESC NULLS LAST, m.title ASC
LIMIT %(limit)s;
"""

SQL_CATALOG_SIMILARITY_FOR_PLATFORM = f"""
WITH combined_presence AS (
  SELECT 
    p.uid,
    MAX(CASE WHEN p.iso_alpha2 = %(country_a)s THEN 1 ELSE 0 END) AS in_a,
    MAX(CASE WHEN p.iso_alpha2 = %(country_b)s THEN 1 ELSE 0 END) AS in_b
  FROM {PRES_TBL} p
  WHERE {PLATFORM_FILTER}
    AND p.iso_alpha2 IN (%(country_a)s, %(country_b)s)
    AND p.out_on IS NULL
  GROUP BY p.uid
)
SELECT
  SUM(in_a) AS total_a,
  SUM(in_b) AS total_b,
  SUM(in_a * in_b) AS shared,
  SUM(in_a * (1 - in_b)) AS unique_a,
  SUM(in_b * (1 - in_a)) AS unique_b,
  ROUND(
    SUM(in_a * in_b)::numeric 
    / NULLIF(SUM(in_a + in_b - in_a*in_b), 0)
  , 4) AS jaccard
FROM combined_presence;
"""


SQL_PLATFORM_EXCLUSIVITY_SIMPLE = f"""
SELECT 
    m.uid,
    m.title,
    m.type,
    m.year
FROM {PRES_TBL} p
JOIN {META_TBL} m ON m.uid = p.uid
WHERE p.platform_name ILIKE %s
  AND p.iso_alpha2 = %s
  AND p.out_on IS NULL
  AND p.is_exclusive = 'Yes'
ORDER BY m.year DESC NULLS LAST, m.title ASC
LIMIT %s;
"""

SQL_TITLES_IN_A_NOT_IN_B = f"""
WITH in_a AS (
  SELECT DISTINCT p.uid
  FROM {PRES_TBL} p
  WHERE p.out_on IS NULL
    AND {PLATFORM_FILTER}
    AND p.iso_alpha2 = %(country_in)s
),
in_b AS (
  SELECT DISTINCT p.uid
  FROM {PRES_TBL} p
  WHERE p.out_on IS NULL
    AND {PLATFORM_FILTER}
    AND p.iso_alpha2 = %(country_out)s
)
SELECT 
  m.uid,
  m.title,
  INITCAP(m.type) AS type
FROM in_a a
LEFT JOIN in_b b ON b.uid = a.uid
JOIN {META_TBL} m ON m.uid = a.uid
WHERE b.uid IS NULL
ORDER BY m.title
LIMIT %(limit)s;
"""
