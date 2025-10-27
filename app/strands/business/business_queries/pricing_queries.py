from src.strands.infrastructure.database.constants import *


# =============================================================================
# LATEST PRICES - Último precio por hash_unique
# =============================================================================
# OPTIMIZACIONES:
# - Eliminado CTE innecesario, movido al WHERE principal
# - DISTINCT ON más eficiente que ROW_NUMBER() para últimos registros
# - Índice recomendado: CREATE INDEX idx_prices_hash_created ON prices (hash_unique, created_at DESC);

SQL_LATEST_PRICE = f"""
SELECT DISTINCT ON (pr.hash_unique)
  pr.hash_unique, pr.platform_code, pr.price_type, pr.price, pr.currency,
  pr.definition, pr.license, pr.out_on, pr.created_at
FROM {PRICES_TBL} pr
{{JOIN_PRES}}
WHERE {{WHERE_SCOPES}}
  AND {{EXTRA_FILTERS}}
ORDER BY pr.hash_unique, pr.created_at DESC NULLS LAST
LIMIT %s;
"""

# =============================================================================
# PRICE HISTORY - Histórico completo de precios
# =============================================================================
# OPTIMIZACIONES:
# - Simplificado, eliminando COALESCE innecesario si created_at no es NULL
# - Si created_at puede ser NULL, mantener COALESCE pero crear índice con expresión
# - Índice: CREATE INDEX idx_prices_created_desc ON prices (created_at DESC NULLS LAST);

SQL_PRICE_HISTORY = f"""
{{HEAD_CTE}}
SELECT
  pr.hash_unique, pr.platform_code, pr.price_type, pr.price, pr.currency,
  pr.definition, pr.license, pr.out_on, pr.created_at
FROM {PRICES_TBL} pr
{{FROM_JOIN}}
{{WHERE_CLAUSE}}
ORDER BY pr.created_at DESC NULLS LAST
LIMIT %s;
"""

# Versión optimizada si no necesitas todas las columnas
SQL_PRICE_HISTORY_LIGHT = f"""
{{HEAD_CTE}}
SELECT
  pr.hash_unique, pr.platform_code, pr.price_type, pr.price, pr.currency,
  pr.created_at
FROM {PRICES_TBL} pr
{{FROM_JOIN}}
{{WHERE_CLAUSE}}
ORDER BY pr.created_at DESC NULLS LAST
LIMIT %s;
"""

# =============================================================================
# PRICE CHANGES - Cambios de precio en ventana temporal
# =============================================================================
# OPTIMIZACIONES:
# - WINDOW clause nombrada (más legible y eficiente)
# - Eliminado COALESCE repetido
# - Partición simplificada agrupando campos constantes
# - IMPORTANTE: El filtro temporal se aplica en el código Python, NO en la query
# - Índice: CREATE INDEX idx_prices_hash_platform_created ON prices 
#           (hash_unique, platform_code, price_type, definition, license, currency, created_at);

SQL_PRICE_CHANGES = f"""
WITH scoped AS (
  SELECT pr.*
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  {{WHERE_SCOPES}}
),
ordered AS (
  SELECT
    s.hash_unique,
    s.platform_code,
    s.price_type,
    s.definition,
    s.license,
    s.currency,
    s.price,
    s.created_at,
    LAG(s.price) OVER w AS prev_price,
    LAG(s.created_at) OVER w AS prev_ts
  FROM scoped s
  WINDOW w AS (
    PARTITION BY s.hash_unique, s.platform_code, s.price_type, 
                 s.definition, s.license, s.currency
    ORDER BY s.created_at
  )
)
SELECT
  o.hash_unique,
  o.platform_code,
  o.price_type,
  o.definition,
  o.license,
  o.currency,
  o.prev_price,
  o.price,
  (o.price - o.prev_price) AS delta,
  o.created_at,
  o.created_at AS current_ts,
  o.prev_ts AS previous_ts
FROM ordered o
WHERE o.prev_price IS NOT NULL
{{DIRECTION}}
ORDER BY (o.price - o.prev_price) {{DELTA_ORDER}}, o.created_at DESC
LIMIT %s;
"""

# =============================================================================
# PRICE STATS - Estadísticas agregadas de precios
# =============================================================================
# OPTIMIZACIONES:
# - Usar approximate percentile si la precisión exacta no es crítica (mucho más rápido)
# - Índice: CREATE INDEX idx_prices_group_stats ON prices 
#           (platform_code, price_type, currency, definition, license) 
#           INCLUDE (price);

SQL_PRICE_STATS = f"""
SELECT
  pr.platform_code,
  pr.price_type,
  pr.currency,
  pr.definition,
  pr.license,
  COUNT(*)::integer AS samples,
  MIN(pr.price) AS min_price,
  MAX(pr.price) AS max_price,
  AVG(pr.price)::numeric(18,2) AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.price)::numeric(18,2) AS median_price
FROM {PRICES_TBL} pr
{{JOIN_PRES}}
{{WHERE_SCOPES}}
GROUP BY pr.platform_code, pr.price_type, pr.currency, pr.definition, pr.license
ORDER BY pr.platform_code, pr.price_type, pr.definition, pr.license;
"""

# Versión alternativa ultra-rápida con aproximación (para datasets grandes > 100k)
SQL_PRICE_STATS_FAST = f"""
SELECT
  pr.platform_code,
  pr.price_type,
  pr.currency,
  pr.definition,
  pr.license,
  COUNT(*)::integer AS samples,
  MIN(pr.price) AS min_price,
  MAX(pr.price) AS max_price,
  AVG(pr.price)::numeric(18,2) AS avg_price,
  PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY pr.price)::numeric(18,2) AS median_price
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
# OPTIMIZACIONES:
# - Eliminado GROUP BY redundante en primer CTE
# - Movido filtro de hash_unique a JOIN en lugar de subquery
# - ARRAY_AGG optimizado con DISTINCT en lugar de subquery
# - Índices: 
#   CREATE INDEX idx_pres_uid_platform ON pres (uid, platform_name, hash_unique);
#   CREATE INDEX idx_prices_hash ON prices (hash_unique) INCLUDE (definition, license);

SQL_HITS_Q_GLOBAL = """
WITH pres AS (
  SELECT DISTINCT platform_name, hash_unique
  FROM {PRES}
  WHERE uid = %s
),
filtered_prices AS (
  SELECT p.platform_name, pr.hash_unique
  FROM pres p
  JOIN {PRICES} px ON px.hash_unique = p.hash_unique
  {DEF_FILTER}
  {LIC_FILTER}
),
with_countries AS (
  SELECT fp.platform_name, pr.iso_alpha2
  FROM filtered_prices fp
  JOIN {PRES} pr ON pr.hash_unique = fp.hash_unique
)
SELECT 
  wc.platform_name,
  ARRAY_AGG(DISTINCT wc.iso_alpha2 ORDER BY wc.iso_alpha2) AS countries
FROM with_countries wc
GROUP BY wc.platform_name
ORDER BY wc.platform_name
LIMIT %s;
"""

SQL_HITS_Q_BY_COUNTRY = """
WITH pres AS (
  SELECT DISTINCT pr.platform_name, pr.hash_unique
  FROM {PRES} pr
  WHERE pr.iso_alpha2 = %s
    AND pr.uid = %s
)
SELECT DISTINCT
  p.platform_name,
  %s AS country
FROM pres p
WHERE EXISTS (
  SELECT 1
  FROM {PRICES} x
  WHERE x.hash_unique = p.hash_unique
  {DEF_FILTER}
  {LIC_FILTER}
)
ORDER BY p.platform_name
LIMIT %s;
"""

# =============================================================================
# ÍNDICES RECOMENDADOS (basados en columnas reales)
# =============================================================================
"""
-- ============================================================================
-- CRÍTICOS - Crear PRIMERO (máximo impacto)
-- ============================================================================

-- 1. Para LATEST_PRICE (DISTINCT ON optimizado)
CREATE INDEX CONCURRENTLY idx_prices_hash_created 
  ON new_cp_presence_prices (hash_unique, created_at DESC NULLS LAST);

-- 2. Para PRICE_HISTORY (ORDER BY created_at)
CREATE INDEX CONCURRENTLY idx_prices_created_desc 
  ON new_cp_presence_prices (created_at DESC NULLS LAST);

-- 3. Para búsquedas por hash_unique (usado en todos los queries)
CREATE INDEX CONCURRENTLY idx_prices_hash_unique 
  ON new_cp_presence_prices (hash_unique);

-- ============================================================================
-- ALTA PRIORIDAD - Para queries de cambios y estadísticas
-- ============================================================================

-- 4. Para PRICE_CHANGES (LAG/LEAD window functions)
-- Este es CRÍTICO si PRICE_CHANGES es frecuente
CREATE INDEX CONCURRENTLY idx_prices_changes 
  ON new_cp_presence_prices (
    hash_unique, 
    platform_code, 
    price_type, 
    definition, 
    license, 
    currency, 
    created_at
  );

-- 5. Para PRICE_STATS (GROUP BY + agregaciones)
CREATE INDEX CONCURRENTLY idx_prices_stats 
  ON new_cp_presence_prices (
    platform_code, 
    price_type, 
    currency, 
    definition, 
    license
  ) INCLUDE (price);

-- ============================================================================
-- MEDIA PRIORIDAD - Filtros comunes
-- ============================================================================

-- 6. Para filtros por plataforma
CREATE INDEX CONCURRENTLY idx_prices_platform 
  ON new_cp_presence_prices (platform_code);

-- 7. Para filtros por tipo de precio
CREATE INDEX CONCURRENTLY idx_prices_type 
  ON new_cp_presence_prices (price_type);

-- 8. Para filtros por definición + licencia (combinados frecuentemente)
CREATE INDEX CONCURRENTLY idx_prices_def_lic 
  ON new_cp_presence_prices (definition, license);

-- ============================================================================
-- OPCIONAL - Solo si tienes problemas de performance específicos
-- ============================================================================

-- 9. Para rangos de fechas (entered_on, out_on)
CREATE INDEX CONCURRENTLY idx_prices_entered_on 
  ON new_cp_presence_prices (entered_on) 
  WHERE entered_on IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_prices_out_on 
  ON new_cp_presence_prices (out_on) 
  WHERE out_on IS NOT NULL;

-- 10. Índice compuesto para filtros complejos en PRICE_CHANGES
-- Solo si haces filtros por fecha + plataforma frecuentemente
CREATE INDEX CONCURRENTLY idx_prices_created_platform 
  ON new_cp_presence_prices (created_at DESC, platform_code) 
  WHERE created_at >= CURRENT_DATE - INTERVAL '90 days';

-- ============================================================================
-- MANTENIMIENTO
-- ============================================================================

-- Verificar uso de índices después de 1 semana:
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan as index_scans,
  idx_tup_read as tuples_read,
  idx_tup_fetch as tuples_fetched,
  pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE tablename = 'new_cp_presence_prices'
ORDER BY idx_scan DESC;

-- Eliminar índices no usados (idx_scan = 0 después de 1 mes):
-- DROP INDEX CONCURRENTLY idx_nombre_no_usado;

-- ============================================================================
-- CONFIGURACIÓN ADICIONAL (opcional, evaluar en producción)
-- ============================================================================

-- Si la tabla es muy grande (>10M registros), considera:
ALTER TABLE new_cp_presence_prices SET (fillfactor = 90);

-- Ajustar autovacuum para tabla de alta inserción:
ALTER TABLE new_cp_presence_prices SET (
  autovacuum_vacuum_scale_factor = 0.05,
  autovacuum_analyze_scale_factor = 0.02
);
"""