from src.sql.utils.constants_sql import *

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
