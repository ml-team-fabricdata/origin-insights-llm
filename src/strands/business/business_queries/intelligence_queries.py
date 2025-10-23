from src.strands.infrastructure.database.constants import *


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

SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY = f"""
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
"""


# Similitud de catálogo entre países para una plataforma
SQL_CATALOG_SIMILARITY_FOR_PLATFORM = f"""
WITH combined_presence AS (
  SELECT 
    p.uid,
    MAX(CASE WHEN p.iso_alpha2 = %s THEN 1 ELSE 0 END) AS in_country_a,
    MAX(CASE WHEN p.iso_alpha2 = %s THEN 1 ELSE 0 END) AS in_country_b
  FROM {PRES_TBL} p
  WHERE p.platform_name ILIKE %s
    AND p.iso_alpha2 IN (%s, %s)
    AND (p.out_on IS NULL)
  GROUP BY p.uid
)
SELECT
  SUM(in_country_a) AS total_a,
  SUM(in_country_b) AS total_b,  
  SUM(in_country_a * in_country_b) AS shared,
  SUM(in_country_a * (1 - in_country_b)) AS unique_a,
  SUM(in_country_b * (1 - in_country_a)) AS unique_b
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
SELECT
  m.uid,
  m.title,
  INITCAP(m.type) AS type,
  STRING_AGG(DISTINCT p_in.platform_name, ', ' ORDER BY p_in.platform_name) AS platforms_in,
  STRING_AGG(DISTINCT p_in.iso_alpha2, ', ' ORDER BY p_in.iso_alpha2) AS countries_in
FROM {META_TBL} m
JOIN {PRES_TBL} p_in ON p_in.uid = m.uid
  AND {{in_condition}}
  AND (p_in.out_on IS NULL)
  {{pin_filter}}
WHERE NOT EXISTS (
  SELECT 1
  FROM {PRES_TBL} p_out
  WHERE p_out.uid = m.uid
    AND {{out_condition}}
    AND (p_out.out_on IS NULL)
    {{pout_filter}}
)
GROUP BY m.uid, m.title, m.type
ORDER BY m.title
LIMIT {{limit_placeholder}};
"""
