from src.sql.utils.constants_sql import *

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
  ORDER BY pr.hash_unique, pr.created_at DESC
)
SELECT *
FROM prices_filtered
WHERE {{EXTRA_FILTERS}}
ORDER BY created_at DESC
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

SQL_BATCH_PRICES = f"""
SELECT 
  unnest(%(hashes)s::text[]) AS hash_unique,
  pr.*
FROM {PRICES_TBL} pr
WHERE pr.hash_unique = ANY(%(hashes)s::text[])
  {{CONDITIONS}}
ORDER BY pr.hash_unique, pr.created_at DESC;
"""

SQL_PRICE_TRENDS = f"""
WITH daily_prices AS (
  SELECT 
    DATE(created_at) AS price_date,
    platform_code,
    currency,
    AVG(price) AS avg_price,
    COUNT(*) AS sample_count
  FROM {PRICES_TBL}
  WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    {{CONDITIONS}}
  GROUP BY DATE(created_at), platform_code, currency
)
SELECT 
  price_date,
  platform_code,
  currency,
  avg_price,
  sample_count,
  avg_price - LAG(avg_price) OVER (
    PARTITION BY platform_code, currency 
    ORDER BY price_date
  ) AS daily_change
FROM daily_prices
ORDER BY price_date DESC, platform_code;
"""

# =============================================================================
# PLATFORM & AVAILABILITY
# =============================================================================

QUERY_PLATFORMS_FOR_TITLE = f"""
SELECT 
  p.uid,
  p.platform_name,
  p.platform_country,
  p.iso_alpha2 AS country,
  p.out_on
FROM {PRES_TBL} p
WHERE p.uid = %s 
  AND p.out_on IS NULL
ORDER BY p.platform_name, p.iso_alpha2
LIMIT %s;
"""

QUERY_PLATFORMS_FOR_TITLE_BY_COUNTRY = f"""
SELECT 
  p.uid,
  p.platform_name,
  p.platform_country,
  p.iso_alpha2 AS country,
  p.registry_status,
  p.in_on,
  p.out_on
FROM {PRES_TBL} p
WHERE p.uid = %s 
  AND p.iso_alpha2 = %s
  AND (p.out_on IS NULL OR p.registry_status = 'active')
ORDER BY p.platform_name ASC, p.platform_country ASC;
"""

QUERY_AVAILABILITY_WITH_PRICES = f"""
WITH active_presence AS (
  SELECT 
    p.platform_name,
    p.iso_alpha2 AS country_iso2,
    p.permalink,
    p.uid,
    p.hash_unique,
    p.is_exclusive,
    p.plan_name
  FROM {PRES_TBL} p
  WHERE p.uid = %(uid)s
    AND p.out_on IS NULL
    {{country_condition}}
),
latest_prices AS (
  SELECT DISTINCT ON (pr.hash_unique)
    pr.hash_unique,
    pr.price,
    pr.currency,
    pr.price_type,
    pr.definition,
    pr.license,
    pr.created_at
  FROM {PRICES_TBL} pr
  WHERE pr.hash_unique IN (SELECT hash_unique FROM active_presence)
  ORDER BY pr.hash_unique, pr.created_at DESC
)
SELECT 
  ap.*,
  lp.price,
  lp.currency,
  lp.price_type,
  lp.definition,
  lp.license,
  lp.created_at AS price_updated_at
FROM active_presence ap
LEFT JOIN latest_prices lp ON lp.hash_unique = ap.hash_unique
ORDER BY ap.platform_name, lp.price NULLS LAST;
"""

# =============================================================================
# PREMIERES & TRENDS
# =============================================================================


QUERY_RECENT_PREMIERES = f"""
SELECT 
  m.uid,
  m.title,
  m.type,
  m.year,
  STRING_AGG(DISTINCT p.platform_name, ', ') AS platforms,
  STRING_AGG(DISTINCT p.platform_country, ', ') AS platform_countries
FROM {META_ALL} m
JOIN {PRES_TBL} p ON p.uid = m.uid
WHERE p.iso_alpha2 = %(country)s
  AND (p.out_on IS NULL)
  AND m.release_date BETWEEN %(date_from)s AND %(date_to)s
GROUP BY m.uid, m.title, m.type, m.year, m.release_date
ORDER BY m.release_date DESC NULLS LAST
LIMIT %(limit)s;
"""

# Estrenos por país (con EXISTS)
QUERY_RECENT_PREMIERES_BY_COUNTRY = f"""
SELECT 
  m.uid,
  m.title,
  m.type,
  m.year,
  m.release_date,
  (
    SELECT STRING_AGG(DISTINCT platform_name, ', ' ORDER BY platform_name)
    FROM {PRES_TBL} p
    WHERE p.uid = m.uid 
      AND p.iso_alpha2 = %(country)s
      AND p.out_on IS NULL
  ) AS platforms
FROM {META_ALL} m
WHERE m.release_date BETWEEN %(date_from)s AND %(date_to)s
  AND EXISTS (
    SELECT 1 FROM {PRES_TBL} p
    WHERE p.uid = m.uid 
      AND p.iso_alpha2 = %(country)s
      AND p.out_on IS NULL
  )
ORDER BY m.release_date DESC
LIMIT %(limit)s;
"""

# Estrenos rankeados por pico de hits
QUERY_RECENT_TOP_PREMIERES = f"""
WITH base AS (
  SELECT 
    m.uid,
    m.title,
    m.type,
    m.year,
    m.release_date,
    STRING_AGG(DISTINCT p.platform_name, ', ') AS platforms,
    STRING_AGG(DISTINCT p.platform_country, ', ') AS platform_countries
  FROM {META_TBL} m
  JOIN {PRES_TBL} p ON p.uid = m.uid
  WHERE {{where_clauses}}
  GROUP BY m.uid, m.title, m.type, m.year, m.release_date
),
scored AS (
  SELECT
    b.*,
    MAX(h.hits) AS peak_hits,
    MAX(h.date) FILTER (
      WHERE h.hits = (
        SELECT MAX(h2.hits) FROM {HITS_GLOBAL_TBL} h2
        WHERE h2.uid = b.uid AND h2.date BETWEEN %s AND %s
      )
    ) AS peak_hits_date
  FROM base b
  LEFT JOIN {HITS_GLOBAL_TBL} h
    ON h.uid = b.uid
   AND h.date BETWEEN %s AND %s
  GROUP BY b.uid, b.title, b.type, b.year, b.release_date, 
           b.platforms, b.platform_countries
)
SELECT *
FROM scored
ORDER BY peak_hits DESC NULLS LAST, release_date DESC NULLS LAST, 
         title ASC
LIMIT {{limit}};
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

# =============================================================================
# PRESENCE & COUNTRY STATS
# =============================================================================

QUERY_PRESENCE_STATISTICS = f"""
SELECT
  COUNT(*) AS total_records,
  COUNT(DISTINCT p.platform_name) AS unique_platforms,
  COUNT(DISTINCT p.iso_alpha2) AS unique_countries,
  COUNT(DISTINCT p.uid) AS unique_content,
  AVG(p.duration)::numeric(10,2) AS avg_duration,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.duration) AS median_duration,
  COUNT(*) FILTER (WHERE p.is_exclusive = 'true') AS exclusive_count,
  COUNT(*) FILTER (WHERE p.is_kids = 'true') AS kids_content_count,
  COUNT(*) FILTER (WHERE p.type = 'Movie') AS movie_count,
  COUNT(*) FILTER (WHERE p.type = 'Series') AS series_count
FROM {PRES_TBL} p
{{where_clause}};
"""

SQL_PRESENCE_WITH_PRICE_OPTIMIZED = f"""
WITH filtered_presence AS (
  SELECT 
    p.*,
    ROW_NUMBER() OVER (ORDER BY p.clean_title, p.platform_name) AS rn
  FROM {PRES_TBL} p
  WHERE {{WHERE_CONDITIONS}}
  LIMIT {{LIMIT}} OFFSET {{OFFSET}}
),
latest_prices AS (
  SELECT DISTINCT ON (pr.hash_unique)
    pr.hash_unique,
    pr.price,
    pr.currency,
    pr.price_type,
    pr.definition,
    pr.license,
    pr.created_at
  FROM {PRICES_TBL} pr
  WHERE pr.hash_unique IN (SELECT hash_unique FROM filtered_presence)
    {{PRICE_CONDITIONS}}
  ORDER BY pr.hash_unique, pr.created_at DESC
)
SELECT 
  fp.*,
  lp.price AS price_amount,
  lp.currency AS price_currency,
  lp.price_type,
  lp.definition AS price_definition,
  lp.license AS price_license,
  lp.created_at AS price_created_at
FROM filtered_presence fp
LEFT JOIN latest_prices lp ON lp.hash_unique = fp.hash_unique
ORDER BY fp.rn;
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
{{joins_clause}}
{{where_clause}}
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

# =============================================================================
# EXCLUSIVITY & SIMILARITY
# =============================================================================

# Exclusividad por país
SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY = f"""
WITH platform_analysis AS (
  SELECT 
    p.uid,
    COUNT(DISTINCT p.platform_name) AS n_platforms,
    BOOL_OR(p.platform_name = %s) AS on_target_platform,
    -- Precalcular estadísticas globales con window functions
    COUNT(*) FILTER (WHERE p.platform_name = %s) OVER () AS total_on_platform,
    COUNT(DISTINCT p.uid) FILTER (WHERE p.platform_name = %s) OVER () AS unique_on_platform
  FROM {PRES_TBL} p
  WHERE p.iso_alpha2 = %s 
    AND (p.out_on IS NULL)
  GROUP BY p.uid
),
exclusives_with_stats AS (
  SELECT 
    uid,
    -- Usar la estadística precalculada
    COUNT(*) OVER () AS exclusive_count,
    unique_on_platform,
    ROUND(COUNT(*) OVER () * 100.0 / NULLIF(unique_on_platform, 0), 2) AS exclusivity_pct
  FROM platform_analysis
  WHERE on_target_platform AND n_platforms = 1
)
SELECT 
  m.uid, 
  m.title, 
  m.type, 
  m.year,
  e.exclusive_count::int AS exclusive_titles,
  e.unique_on_platform::int AS total_titles_on_platform,
  e.exclusivity_pct
FROM exclusives_with_stats e
JOIN {META_TBL} m ON m.uid = e.uid
ORDER BY m.year DESC NULLS LAST, m.title ASC
LIMIT %s;
"""

# Similitud de catálogo entre países para una plataforma
SQL_CATALOG_SIMILARITY_FOR_PLATFORM = f"""
WITH combined_presence AS (
  SELECT 
    p.uid,
    CASE WHEN p.iso_alpha2 = %s THEN 1 ELSE 0 END AS in_country_a,
    CASE WHEN p.iso_alpha2 = %s THEN 1 ELSE 0 END AS in_country_b
  FROM {PRES_TBL} p
  WHERE p.platform_name = %s
    AND p.iso_alpha2 IN (%s, %s)
    AND (p.out_on IS NULL)
  GROUP BY p.uid  -- Elimina duplicados si un título está múltiples veces
  HAVING MAX(CASE WHEN p.iso_alpha2 = %s THEN 1 ELSE 0 END) = 1 
      OR MAX(CASE WHEN p.iso_alpha2 = %s THEN 1 ELSE 0 END) = 1
)
SELECT
  SUM(in_country_a) AS total_a,
  SUM(in_country_b) AS total_b,  
  SUM(in_country_a * in_country_b) AS shared,
  SUM(in_country_a * (1 - in_country_b)) AS unique_a,
  SUM(in_country_b * (1 - in_country_a)) AS unique_b
FROM combined_presence;
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

# =============================================================================
# TOP (UNIFICADAS)
# =============================================================================

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
WHERE m.uid = %s
GROUP BY m.uid, m.title, m.year, m.type, h.hits;
"""

# Exclusivos por plataforma/país
PLATFORM_EXCLUSIVES_SQL = """
SELECT m.uid, m.clean_title, m.type
FROM ms.new_cp_presence m
WHERE m.platform_name = %s
  AND m.iso_alpha2   = %s
  AND (m.out_on IS NULL)
LIMIT %s;
"""

# Comparar plataformas para un título exacto
COMPARE_PLATFORMS_FOR_TITLE_SQL = """
SELECT DISTINCT
  p.platform_name,
  p.platform_country
FROM ms.new_cp_presence p
JOIN ms.metadata_simple_all m 
  ON m.uid = p.uid
WHERE m.title ILIKE %s
  AND (p.out_on IS NULL)
ORDER BY p.platform_name;
"""

# Top por país (con y sin año)
TOP_BY_COUNTRY_SQL = """
SELECT
  m.uid,
  m.title,
  m.type,
  h.hits,
  h.date,
  h.year
FROM ms.hits_global h
JOIN ms.metadata_simple_all m ON m.uid = h.uid
WHERE m.countries_iso = %s
  AND h.currentyear = %s
GROUP BY m.uid, m.title, m.type, h.hits, h.date, h.year
ORDER BY h.hits DESC
LIMIT %s;
"""

TOP_BY_COUNTRY_NO_YEAR_SQL = """
SELECT
  m.uid,
  m.title,
  m.type,
  h.hits,
  h.date,
  h.year
FROM ms.hits_global h
JOIN ms.metadata_simple_all m ON m.uid = h.uid
WHERE m.countries_iso = %s
GROUP BY m.uid, m.title, m.type, h.hits, h.date, h.year
ORDER BY h.hits DESC
LIMIT %s;
"""

# Top por género/año
TOP_BY_GENRE_SQL = """
SELECT
  m.uid,
  m.title,
  m.type,
  h.hits,
  h.date,
  h.year
FROM ms.hits_global h
JOIN ms.metadata_simple_all m ON m.uid = h.uid
WHERE m.primary_genre = %s
  AND h.currentyear = %s
GROUP BY m.uid, m.title, m.type, h.hits, h.date, h.year
ORDER BY h.hits DESC
LIMIT %s;
"""

# Top por tipo/año
TOP_BY_TYPE_SQL = """
SELECT
  m.uid,
  m.title,
  m.type,
  h.hits,
  h.date,
  h.year
FROM ms.hits_global h
JOIN ms.metadata_simple_all m ON m.uid = h.uid
WHERE m.type = %s
  AND h.currentyear = %s
GROUP BY m.uid, m.title, m.type, h.hits, h.date, h.year
ORDER BY h.hits DESC
LIMIT %s;
"""

# =============================================================================
# UTILITIES
# =============================================================================

SQL_CHECK_EXISTS = """
SELECT EXISTS(
  SELECT 1 FROM {TABLE} WHERE {COLUMN} = %s
) AS exists;
"""

SQL_GET_HASHES_BY_UID = f"""
SELECT p.hash_unique
FROM {PRES_TBL} p
WHERE {{WHERE_CONDITIONS}}
  AND p.hash_unique IS NOT NULL
ORDER BY p.created_at DESC
LIMIT 1000;
"""
