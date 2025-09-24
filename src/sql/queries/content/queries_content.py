from src.sql.utils.constants_sql import *

# =============================================================================
# TITLES
# =============================================================================

FILMOGRAPHY_SQL = f"""
SELECT *
FROM {METADATA_TABLE} m
WHERE m.uid = %s
"""

RATING_QUERY_COUNTRY = f"""
    SELECT
        m.uid,
        m.title,
        m.year,
        m.type,
        SUM(h.hits) AS total_hits,
        AVG(h.hits) AS avg_hits,
        COUNT(h.hits) AS hit_count
    FROM {META_TBL} m
    LEFT JOIN {HITS_PRESENCE_TBL} h ON m.uid = h.uid
    WHERE m.uid = %s
    AND m.country ILIKE %s
    GROUP BY m.uid, m.title, m.year, m.type
"""

RATING_QUERY_GLOBAL = f""" SELECT
                m.uid,
                m.title,
                m.year,
                m.type,
            SUM(h.hits) AS total_hits,
            AVG(h.hits) AS avg_hits,
            COUNT(h.hits) AS hit_count
            FROM {META_TBL} m
            LEFT JOIN {HITS_GLOBAL_TBL} h ON m.uid = h.uid
            WHERE m.uid = %s
            GROUP BY m.uid, m.title, m.year, m.type, h.hits
"""

# =============================================================================
# METADATA
# =============================================================================

METADATA_COUNT_SQL = """
SELECT COUNT(*)::bigint AS total 
FROM {table_name}
{where_clause};
"""

METADATA_LIST_SQL = """
SELECT uid, title, type, year, duration, countries_iso
FROM {table_name}
{where_clause}
ORDER BY {order_by} {order_dir}, uid
LIMIT %s;
"""

METADATA_DISTINCT_SQL = """
SELECT DISTINCT {column} AS value
FROM {table_name}
WHERE {column} IS NOT NULL AND {column} != ''
ORDER BY 1
LIMIT %s;
"""

METADATA_STATS_SQL = f"""
SELECT
  COUNT(*)::bigint                                      AS total,
  MIN(year)                                             AS min_year,
  MAX(year)                                             AS max_year,
  ROUND(AVG(duration)::numeric, 2)                      AS avg_duration,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration)::numeric, 2) AS median_duration
FROM {META_TBL}
{{where_clause}};
"""

METADATA_BASIC_INFO_SQL = f"""
SELECT uid, title, type, year, duration 
FROM {META_TBL} 
WHERE uid = %s;
"""

METADATA_ADVANCED_COUNT_SQL = f"""
SELECT COUNT(*) AS cnt 
FROM {META_TBL}
{{where_clause}};
"""

METADATA_ADVANCED_SELECT_SQL = f"""
SELECT {{select_cols}}
FROM {META_TBL}
{{where_clause}}
ORDER BY {{order_by}} {{order_dir}}, title ASC
LIMIT {{limit}} OFFSET {{offset}};
"""
