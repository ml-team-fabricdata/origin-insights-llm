from src.strands.utils.constants_sql import *

# =============================================================================
# PRICE QUERIES
# =============================================================================

SQL_LATEST_PRICE = f"""
WITH prices_filtered AS (
  SELECT DISTINCT ON (pr.hash_unique)
    pr.hash_unique, 
    pr.platform_code, 
    pr.price_type, 
    pr.price, 
    pr.currency,
    pr.definition, 
    pr.license, 
    pr.out_on, 
    pr.created_at
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  WHERE {{WHERE_SCOPES}}
)
SELECT *
FROM prices_filtered
WHERE {{EXTRA_FILTERS}}
LIMIT %s;
"""

SQL_PRICE_HISTORY = f"""
SELECT
  pr.hash_unique, 
  pr.platform_code, 
  pr.price_type, 
  pr.price, 
  pr.currency,
  pr.definition, 
  pr.license, 
  pr.out_on, 
  pr.created_at
FROM {PRICES_TBL} pr
{{JOIN_CONDITIONS}}
WHERE {{WHERE_CLAUSE}}
ORDER BY pr.created_at DESC
LIMIT %s;
"""

SQL_PRICE_CHANGES = f"""
WITH price_windows AS (
  SELECT 
    pr.hash_unique,
    pr.platform_code,
    pr.price_type,
    pr.definition,
    pr.license,
    pr.currency,
    pr.price,
    pr.created_at,
    LAG(pr.price, 1) OVER w AS prev_price,
    LAG(pr.created_at, 1) OVER w AS prev_ts
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  WHERE {{WHERE_SCOPES}}
    AND pr.created_at >= CURRENT_DATE - %s::interval
  WINDOW w AS (
    PARTITION BY pr.hash_unique, pr.platform_code, pr.price_type, 
                 pr.definition, pr.license, pr.currency
    ORDER BY pr.created_at
  )
)
SELECT 
  hash_unique,
  platform_code,
  price_type,
  definition,
  license,
  currency,
  prev_price,
  price,
  (price - prev_price) AS delta,
  created_at AS current_ts,
  prev_ts AS previous_ts
FROM price_windows
WHERE prev_price IS NOT NULL
  {{DIRECTION_FILTER}}
ORDER BY ABS(price - prev_price) DESC, created_at DESC
LIMIT %s;
"""

SQL_PRICE_STATS = f"""
SELECT
  pr.platform_code,
  pr.price_type,
  pr.currency,
  pr.definition,
  pr.license,
  COUNT(*) AS samples,
  MIN(pr.price) AS min_price,
  MAX(pr.price) AS max_price,
  AVG(pr.price)::numeric(10,2) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.price)::numeric(10,2) AS median_price
FROM {PRICES_TBL} pr
{{JOIN_PRES}}
WHERE {{WHERE_SCOPES}}
GROUP BY ROLLUP(
  pr.platform_code, 
  pr.price_type, 
  pr.currency, 
  pr.definition, 
  pr.license
)
HAVING pr.platform_code IS NOT NULL
ORDER BY pr.platform_code, pr.price_type, pr.definition, pr.license;
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
