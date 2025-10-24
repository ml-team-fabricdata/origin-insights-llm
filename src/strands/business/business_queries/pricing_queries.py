from src.strands.infrastructure.database.constants import *


# =============================================================================
# LATEST PRICES - Último precio por hash_unique
# =============================================================================

SQL_LATEST_PRICE = f"""
WITH prices_scoped AS (
  SELECT pr.*
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  {{WHERE_SCOPES}}
),
ranked AS (
  SELECT ps.*,
         ROW_NUMBER() OVER (
           PARTITION BY ps.hash_unique
           ORDER BY COALESCE(ps.created_at) DESC
         ) AS rn
  FROM prices_scoped ps
)
SELECT
  r.hash_unique, r.platform_code, r.price_type, r.price, r.currency,
  r.definition, r.license, r.out_on, r.created_at
FROM ranked r
WHERE r.rn = 1
{{EXTRA_FILTERS}}
ORDER BY r.created_at DESC NULLS LAST
LIMIT %s;
"""

# =============================================================================
# PRICE HISTORY - Histórico completo de precios
# =============================================================================

SQL_PRICE_HISTORY = f"""
{{HEAD_CTE}}
SELECT
  pr.hash_unique, pr.platform_code, pr.price_type, pr.price, pr.currency,
  pr.definition, pr.license, pr.out_on, pr.created_at
FROM {PRICES_TBL} pr
{{FROM_JOIN}}
{{WHERE_CLAUSE}}
ORDER BY COALESCE(pr.created_at) DESC
LIMIT %s;
"""

# =============================================================================
# PRICE CHANGES - Cambios de precio en ventana temporal
# =============================================================================

SQL_PRICE_CHANGES = f"""
WITH scoped AS (
  SELECT pr.*
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  {{WHERE_SCOPES}}
),
ordered AS (
  SELECT
    s.*,
    COALESCE(s.created_at) AS ts,
    LAG(s.price) OVER (
      PARTITION BY s.hash_unique, s.platform_code, s.price_type, s.definition, s.license, s.currency
      ORDER BY COALESCE(s.created_at)
    ) AS prev_price,
    LAG(COALESCE(s.created_at)) OVER (
      PARTITION BY s.hash_unique, s.platform_code, s.price_type, s.definition, s.license, s.currency
      ORDER BY COALESCE(s.created_at)
    ) AS prev_ts
  FROM scoped s
),
since AS (
  SELECT *
  FROM ordered
  WHERE ts >= CURRENT_DATE - %s::interval
)
SELECT
  s.hash_unique,
  s.platform_code,
  s.price_type,
  s.definition,
  s.license,
  s.currency,
  s.prev_price,
  s.price,
  (s.price - s.prev_price) AS delta,
  s.created_at,
  s.ts       AS current_ts,
  s.prev_ts  AS previous_ts
FROM since s
WHERE s.prev_price IS NOT NULL
{{DIRECTION}}
ORDER BY (s.price - s.prev_price) {{DELTA_ORDER}}, s.ts DESC
LIMIT %s;
"""

# =============================================================================
# PRICE STATS - Estadísticas agregadas de precios
# =============================================================================

SQL_PRICE_STATS = f"""
SELECT
  pr.platform_code,
  pr.price_type,
  pr.currency,
  pr.definition,
  pr.license,
  COUNT(*)                                        AS samples,
  MIN(pr.price)                                   AS min_price,
  MAX(pr.price)                                   AS max_price,
  AVG(pr.price)::numeric(18,2)                    AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.price)::numeric(18,2) AS median_price
FROM {PRICES_TBL} pr
{{JOIN_PRES}}
{{WHERE_SCOPES}}
GROUP BY pr.platform_code, pr.price_type, pr.currency, pr.definition, pr.license
ORDER BY pr.platform_code, pr.price_type, pr.definition, pr.license;
"""

# =============================================================================
# HELPER QUERIES - Resolución de hash_unique por UID
# =============================================================================

SQL_GET_HASHES_BY_UID = f"""
SELECT DISTINCT p.hash_unique
FROM {PRES_TBL} p
WHERE {{WHERE_CONDITIONS}}
"""

SQL_DETECT_HASH_EXISTS = f"""
SELECT 1 FROM {PRICES_TBL} WHERE hash_unique = %s LIMIT 1
"""

SQL_DETECT_UID_EXISTS = f"""
SELECT 1 FROM {PRES_TBL} WHERE uid = %s LIMIT 1
"""

# =============================================================================
# HITS WITH QUALITY - Hits + calidad (global / por país)
# =============================================================================

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

