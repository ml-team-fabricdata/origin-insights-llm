from src.strands.utils.constants_sql import *

COMMON_TITLES_ACTOR_DIRECTOR_SQL = f"""
    SELECT DISTINCT
        m.title, 
        m.type, 
        m.year
    FROM {META_TBL} m
    INNER JOIN {ACTED_IN_TABLE} ai ON m.uid = ai.uid
    INNER JOIN {DIRECTED_TABLE} dt ON m.uid = dt.uid
    WHERE ai.cast_id = %s
      AND dt.director_id = %s
    ORDER BY m.year DESC NULLS LAST, m.title
    LIMIT %s
"""
