from src.strands.utils.constants_sql import *

QUERY_PRESENCE_COUNT = f"""
    SELECT COUNT(*)::bigint AS total 
    FROM {PRES_TBL} p 
    {{where_clause}};
"""

QUERY_PRESENCE_LIST = f"""
    SELECT {{select_fields}}
    FROM {PRES_TBL} p
    {{where_clause}}
    ORDER BY p.{{order_by}} {{order_dir}}, p.hash_unique
    LIMIT %(limit)s OFFSET %(offset)s;
"""

QUERY_PRESENCE_DISTINCT = f"""
    SELECT DISTINCT p.{{column}} AS value
    FROM {PRES_TBL} p
    {{where_clause}}
    ORDER BY p.{{column}}
    LIMIT %(limit)s;
"""

QUERY_PRESENCE_STATISTICS = f"""
    SELECT
        COUNT(*)::bigint AS total_records,
        COUNT(DISTINCT p.platform_name) AS unique_platforms,
        COUNT(DISTINCT p.iso_alpha2) AS unique_countries,
        COUNT(DISTINCT p.uid) AS unique_content,
        AVG(p.duration)::numeric(18,2) AS avg_duration,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.duration) AS median_duration,
        COUNT(CASE WHEN p.is_exclusive = 'true' THEN 1 END) AS exclusive_count,
        COUNT(CASE WHEN p.is_kids = 'true' THEN 1 END) AS kids_content_count,
        COUNT(CASE WHEN p.type = 'Movie' THEN 1 END) AS movie_count,
        COUNT(CASE WHEN p.type = 'Series' THEN 1 END) AS series_count
    FROM {PRES_TBL} p
    {{where_clause}};
"""

QUERY_PLATFORM_COUNT_SPECIFIC_COUNTRY = f"""
    SELECT 
        p.iso_alpha2 AS country,
        COUNT(DISTINCT p.platform_name) AS platform_count,
        array_agg(DISTINCT p.platform_name ORDER BY p.platform_name) AS platforms
    FROM {PRES_TBL} p
    WHERE p.iso_alpha2 = %(country_iso)s
        AND p.out_on IS NULL
    GROUP BY p.iso_alpha2;
"""

QUERY_PLATFORM_COUNT_ALL_COUNTRIES = f"""
    SELECT 
        p.iso_alpha2 AS country,
        COUNT(DISTINCT p.platform_name) AS platform_count
    FROM {PRES_TBL} p
    WHERE p.out_on IS NULL
    GROUP BY p.iso_alpha2
    ORDER BY platform_count DESC, p.iso_alpha2;
"""

QUERY_COUNTRY_PLATFORM_SUMMARY = f"""
SELECT
    p.iso_alpha2 AS country,
    COUNT(DISTINCT p.platform_name) AS unique_platforms,
    COUNT(DISTINCT p.uid) AS unique_content,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN p.type = 'Movie' THEN 1 END) AS movies,
    COUNT(CASE WHEN p.type = 'Series' THEN 1 END) AS series,
    COUNT(CASE WHEN p.is_exclusive = 'true' THEN 1 END) AS exclusive_content,
    array_agg(DISTINCT p.platform_name ORDER BY p.platform_name) AS platforms
FROM {PRES_TBL} p
WHERE p.out_on IS NULL
    {{country_condition}}
GROUP BY p.iso_alpha2
ORDER BY unique_platforms DESC, unique_content DESC;
"""
