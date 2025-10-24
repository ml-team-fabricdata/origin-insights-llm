from app.strands.infrastructure.database.constants import *
from app.strands.core.shared_imports import *

SCHEMAS: Dict[str, Tuple[str, ...]] = {
    "ms.metadata_simple_all": (
        "uid", "title", "type", "year", "age", "duration", "synopsis",
        "primary_genre", "genres", "primary_language", "languages",
        "primary_country", "countries", "countries_iso",
        "primary_company", "production_companies", "directors", "full_cast", "writers",
    ),
    "ms.hits_presence_2": (
        "uid", "imdb", "country", "content_type", "date_hits", "hits", "week", "title", "year",
        "piracynormscore", "piracyscore", "imdbnormscore", "imdbscore",
        "twitternormscore", "twitterscore", "youtubenormscore", "youtubescore",
        "input", "piracyplatformsnumber", "tmdb_id", "cdbscore", "cdbnormscore",
        "deltaposition", "position", "poster_image", "deltapositioninit",
        "average", "hits_relative", "currentyear", "release_date", "weeks_since_release",
    ),
    "ms.hits_global": (
        "id", "week", "date", "currentyear", "uid", "imdb", "content_type", "year",
        "imdbscore", "imdbnormscore", "piracyscore", "piracynormscore",
        "hits", "piracyplatformsnumber", "date_hits", "hits_raw",
    ),
    "ms.new_cp_presence": (
        "id", "sql_unique", "enter_on", "out_on", "global_id", "iso_alpha2", "iso_global",
        "platform_country", "platform_name", "platform_code", "package_code", "package_code2",
        "content_id", "hash_unique", "uid", "type", "clean_title", "is_original", "is_kids",
        "is_local", "isbranded", "is_exclusive", "imdb_id", "tmdb_id", "eidr_id", "tvdb_id",
        "duration", "content_status", "registry_status", "uid_updated", "created_at",
    ),
    "ms.new_cp_presence_prices": (
        "id", "hash_unique", "platform_code", "price_type", "price", "currency",
        "definition", "license", "out_on", "created_at"
    ),
}

ALLOWED_TABLES = list(SCHEMAS.keys())

TABLE_MAP = {
    "metadata": "ms.metadata",
    "hits_presence_2": "ms.hits_presence_2",
    "hits_global": "ms.hits_global",
    "new_cp_presence": "ms.new_cp_presence",
    "new_cp_presence_prices": "ms.new_cp_presence_prices",
}

ALLOWED_FUNCS: Dict[str, Tuple[int, int]] = {
    "LOWER": (1, 1), "UPPER": (1, 1), "INITCAP": (1, 1), "TRIM": (1, 1),
    "LENGTH": (1, 1), "SUBSTRING": (2, 3), "COALESCE": (2, -1), "NULLIF": (2, 2),
    "GREATEST": (2, -1), "LEAST": (2, -1), "DATE_TRUNC": (2, 2), "EXTRACT": (2, 2),
    "CAST": (1, 1), "SUM": (1, 1), "AVG": (1, 1), "MIN": (1, 1), "MAX": (1, 1),
    "COUNT": (0, 1), "COUNT_DISTINCT": (1, 1), "ABS": (1, 1), "ROUND": (1, 2),
    "CEIL": (1, 1), "FLOOR": (1, 1),
}

ALLOWED_OPERATORS = {
    "=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "ILIKE",
    "IN", "NOT IN", "IS", "IS NOT", "BETWEEN"
}

ALLOWED_JOIN_TYPES = {
    "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "FULL OUTER JOIN"
}

RESOLVERS: Dict[str, Callable[[Any], Any]] = {}
