from src.sql.utils.constants_sql import *

FILMOGRAPHY_SQL = f"""
SELECT *
FROM {META_TBL} m
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
    AND h.country ILIKE %s
    GROUP BY m.uid, m.title, m.year, m.type
"""

RATING_QUERY_GLOBAL = f"""
    SELECT
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
    GROUP BY m.uid, m.title, m.year, m.type
"""
