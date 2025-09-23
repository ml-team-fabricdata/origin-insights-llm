from src.sql.constants_sql import *

# =============================================================================
# AVAILABILITY QUERIES
# =============================================================================

QUERY_PLATFORMS_FOR_TITLE = f"""
    SELECT 
        p.uid,
        p.platform_name,
        p.platform_country,
        p.iso_alpha2 AS country,
        p.registry_status,
        p.out_on,
        COUNT(*) OVER() AS total_count
    FROM {PRES_TBL} p
    WHERE p.uid = %s 
      AND p.out_on IS NULL
    ORDER BY p.platform_name ASC, p.platform_country ASC, p.iso_alpha2 ASC
    LIMIT %s
"""

QUERY_PLATFORMS_FOR_UID_BY_COUNTRY = f"""
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
      AND p.out_on IS NULL
    ORDER BY p.platform_name ASC, p.platform_country ASC
"""

QUERY_RECENT_PREMIERES_BY_COUNTRY = f"""
    WITH recent_content AS (
        SELECT 
            m.uid,
            m.title,
            m.type,
            m.year,
            m.release_date
        FROM {META_ALL} m
        WHERE m.release_date BETWEEN %(date_from)s AND %(date_to)s
        ORDER BY m.release_date DESC
        LIMIT %(limit)s
    )
    SELECT 
        rc.uid,
        rc.title,
        rc.type,
        rc.year,
        rc.release_date,
        STRING_AGG(DISTINCT p.platform_name, ', ' ORDER BY p.platform_name) AS platforms,
        STRING_AGG(DISTINCT p.platform_country, ', ' ORDER BY p.platform_country) AS platform_countries
    FROM recent_content rc
    JOIN {PRES_TBL} p ON p.uid = rc.uid
    WHERE p.iso_alpha2 = %(country)s
      AND p.out_on IS NULL
    GROUP BY rc.uid, rc.title, rc.type, rc.year, rc.release_date
    ORDER BY rc.release_date DESC NULLS LAST;
"""

QUERY_AVAILABILITY_WITH_PRICES = f"""
    WITH latest_prices AS (
        SELECT DISTINCT ON (hash_unique)
            hash_unique,
            price,
            currency,
            price_type,
            definition,
            license,
            created_at
        FROM {PRICES_TBL}
        WHERE active_only_price IS NULL OR active_only_price = TRUE
        ORDER BY hash_unique, created_at DESC
    )
    SELECT
        p.platform_name AS platform,
        p.iso_alpha2 AS country_iso2,
        p.permalink,
        p.uid,
        p.hash_unique,
        p.out_on,
        p.is_exclusive,
        p.plan_name,
        p.registry_status,
        lp.price,
        lp.currency,
        lp.price_type,
        lp.definition,
        lp.license,
        lp.created_at AS price_updated_at
    FROM {PRES_TBL} p
    LEFT JOIN latest_prices lp ON lp.hash_unique = p.hash_unique
    WHERE p.uid = %(uid)s
        {{country_condition}}
        AND p.out_on IS NULL
    ORDER BY p.platform_name ASC, lp.price ASC NULLS LAST;
"""

QUERY_AVAILABILITY_WITHOUT_PRICES = f"""
    SELECT
        p.platform_name AS platform,
        p.iso_alpha2 AS country_iso2,
        p.permalink,
        p.uid,
        p.hash_unique,
        p.is_exclusive,
        p.plan_name
    FROM {PRES_TBL} p
    WHERE p.uid = %(uid)s
        {{country_condition}}
        AND p.out_on IS NULL
    ORDER BY p.platform_name ASC;
"""

QUERY_PLATFORM_EXCLUSIVES = f"""
    SELECT 
        m.uid, 
        m.clean_title, 
        m.type
    FROM {PRES_TBL} m
    WHERE m.platform_name ILIKE %s
      AND m.iso_alpha2 = %s
      AND m.out_on IS NULL
    LIMIT %s
"""

QUERY_COMPARE_PLATFORM_TITLE = f"""
    SELECT DISTINCT
        p.platform_name,
        p.platform_country
    FROM {PRES_TBL} p
    JOIN {META_TBL} m 
    ON m.uid = p.uid
    WHERE m.title ILIKE %s
        AND p.out_on IS NULL
    ORDER BY p.platform_name
"""

# =============================================================================
# PRESENCE QUERIES
# =============================================================================

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
    {{country_condition}}
    AND p.out_on IS NULL
    GROUP BY p.iso_alpha2
    ORDER BY unique_platforms DESC, unique_content DESC;
"""