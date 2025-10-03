from src.sql.utils.constants_sql import *

QUERY_PLATFORMS_FOR_TITLE = f"""
    SELECT 
        p.uid,
        p.platform_name,
        p.platform_country,
        p.iso_alpha2 AS country,
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
        FROM {META_ALL} m
        WHERE m.release_date BETWEEN %(date_from)s AND %(date_to)s
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
SELECT
  p.platform_name AS platform,
  p.uid,
  p.hash_unique,
  lp.price,
  lp.currency,
  lp.price_type,
  lp.definition,
  lp.license
FROM {PRES_TBL} p
LEFT JOIN LATERAL (
  SELECT price, currency, price_type, definition, license
  FROM {PRICES_TBL} x
  WHERE x.hash_unique = p.hash_unique
  LIMIT 1
) lp ON TRUE
WHERE p.uid = %(uid)s
  {{country_condition}}
ORDER BY p.platform_name ASC, lp.price ASC NULLS LAST;
"""

QUERY_AVAILABILITY_WITHOUT_PRICES = f"""
    SELECT
        p.platform_name,
        p.clean_title
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
