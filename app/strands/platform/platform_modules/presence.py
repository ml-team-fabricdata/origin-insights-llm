from app.strands.infrastructure.database.constants import *
from app.strands.infrastructure.database.utils import *
from app.strands.core.shared_imports import *
from app.strands.platform.platform_queries.queries_presence import *
from app.strands.infrastructure.validators.shared import *
from strands import tool


def build_where_clause(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Build WHERE clause and parameters from filters.
    
    NOTE: Country, platform_name, and type validation handled by validation_node.
    This function expects these fields to already be normalized.
    """
    conditions = []
    params = {}

    conditions.append("p.out_on IS NULL")

    if filters.get("uid"):
        conditions.append("p.uid = %(uid)s")
        params["uid"] = filters["uid"]

    if filters.get("hash_unique"):
        conditions.append("p.hash_unique = %(hash_unique)s")
        params["hash_unique"] = filters["hash_unique"]

    if filters.get("country"):
        conditions.append("p.iso_alpha2 = %(country_iso)s")
        params["country_iso"] = filters["country"]

    if filters.get("platform_name"):
        conditions.append("p.platform_name = %(platform_name)s")
        params["platform_name"] = filters["platform_name"]

    if filters.get("platform_code"):
        conditions.append("p.platform_code = %(platform_code)s")
        params["platform_code"] = filters["platform_code"]

    if filters.get("type"):
        conditions.append("p.type = %(type)s")
        params["type"] = filters["type"]

    if filters.get("title_like"):
        conditions.append("p.clean_title ILIKE %(title_like)s")
        params["title_like"] = build_like_pattern(filters['title_like'])

    for field in ["is_kids", "is_exclusive", "is_original"]:
        if field in filters and filters[field] is not None:
            conditions.append(f"p.{field} = %({field})s")
            params[field] = bool(filters[field])

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else "WHERE 1=1"
    return where_clause, params

def get_select_fields(requested_fields: Optional[List[str]] = None) -> List[str]:
    """Get validated select fields"""
    if not requested_fields:
        return [
            "p.clean_title", "p.uid", "p.hash_unique", "p.platform_name",
            "p.platform_code", "p.iso_alpha2", "p.type", "p.is_kids",
            "p.is_exclusive", "p.plan_name", "p.out_on",
            "p.duration", "p.permalink"
        ]

    validated = []
    for field in requested_fields:
        clean_field = field.strip()
        if clean_field in PRESENCE_ALLOWED_SELECT:
            validated.append(f"p.{clean_field}")

    return validated or ["p.uid", "p.clean_title"]

@tool
def presence_count(country: str = None, platform_name: str = None, uid: str = None, 
                  type: str = None, title_like: str = None) -> List[Dict]:
    """Get SIMPLE COUNT of content presence records (single number only).
    
    Filters: country (ISO-2), platform_name, uid, type (Movie/Series), title_like.
    Returns only total count of matching records.
    Use this for quick counts without detailed data.
    
    Args:
        country: Country ISO-2 code (optional)
        platform_name: Platform name (optional)
        uid: Unique identifier (optional)
        type: Content type - Movie or Series (optional)
        title_like: Title search pattern (optional)
    
    Returns:
        List with single dict containing count
    """
    
    filters = {
        "country": country,
        "platform_name": platform_name,
        "uid": uid,
        "type": type,
        "title_like": title_like
    }
    
    filters = {k: v for k, v in filters.items() if v is not None}

    where_clause, query_params = build_where_clause(filters)
    sql = QUERY_PRESENCE_COUNT.format(where_clause=where_clause)

    result = db.execute_query(sql, query_params)
    return result if result else [{"message": "No results found"}]

@tool
def presence_list(country: str = None, platform_name: str = None, type: str = None,
                 title_like: str = None, limit: int = 25, offset: int = 0,
                 order_by: str = "clean_title", order_dir: str = "ASC") -> List[Dict]:
    """List content presence records with pagination and ordering.
    
    Filters: country (ISO-2), platform_name, type (Movie/Series), title_like.
    Supports pagination (limit, offset) and ordering (order_by with allowed fields, order_dir: ASC/DESC).
    Returns detailed presence information including title, uid, platform details, country, duration, and availability status.
    
    Args:
        country: Country ISO-2 code (optional)
        platform_name: Platform name (optional)
        type: Content type - Movie or Series (optional)
        title_like: Title search pattern (optional)
        limit: Maximum results (default 25)
        offset: Pagination offset (default 0)
        order_by: Field to order by (default 'clean_title')
        order_dir: Order direction - ASC or DESC (default 'ASC')
    
    Returns:
        List of presence records with detailed information
    """
    
    filters = {
        "country": country,
        "platform_name": platform_name,
        "type": type,
        "title_like": title_like
    }
    
    filters = {k: v for k, v in filters.items() if v is not None}
    
    limit = validate_limit(limit, DEFAULT_LIMIT, MAX_LIMIT)
    offset = max(0, int(offset or 0))
    
    if order_by not in PRESENCE_ALLOWED_ORDER:
        order_by = "clean_title"
    
    order_dir = "DESC" if str(order_dir).upper() == "DESC" else "ASC"

    where_clause, query_params = build_where_clause(filters)
    select_fields = get_select_fields()

    sql = QUERY_PRESENCE_LIST.format(
        select_fields=', '.join(select_fields),
        where_clause=where_clause,
        order_by=order_by,
        order_dir=order_dir
    )

    query_params.update({
        "limit": limit,
        "offset": offset
    })

    result = db.execute_query(sql, query_params)
    return result if result else [{"message": "No results found"}]

@tool
def presence_distinct(column: str, country: str = None, platform_name: str = None,
                     type: str = None, limit: int = 100) -> List[Dict]:
    """Get distinct/unique values from presence table columns.
    
    Specify column parameter from allowed list: iso_alpha2, plan_name, platform_code, platform_name, type, content_type.
    Supports optional filters: country, platform_name, type.
    Returns unique values for the specified column, useful for discovering available options and filter values.
    
    Args:
        column: Column name to get distinct values from (required)
        country: Country ISO-2 code filter (optional)
        platform_name: Platform name filter (optional)
        type: Content type filter (optional)
        limit: Maximum results (default 100)
    
    Returns:
        List of distinct values for the specified column
    """
    
    if not column:
        return [{"message": "Column parameter is required"}]

    CP_ALLOWED_COLUMNS = {
        'iso_alpha2', 'plan_name', 'platform_code',
        'platform_name', 'type', 'content_type'
    }

    if column not in CP_ALLOWED_COLUMNS:
        return [{"message": f"Column '{column}' not allowed. Choose from: {sorted(CP_ALLOWED_COLUMNS)}"}]

    filters = {
        "country": country,
        "platform_name": platform_name,
        "type": type
    }
    
    filters = {k: v for k, v in filters.items() if v is not None}
    
    limit = validate_limit(limit, MAX_LIMIT)

    where_clause, query_params = build_where_clause(filters)
    sql = QUERY_PRESENCE_DISTINCT.format(column=column, where_clause=where_clause)
    query_params["limit"] = limit

    result = db.execute_query(sql, query_params)
    return result if result else [{"message": "No results found", "column": column}]

@tool
def presence_statistics(country: str = None, platform_name: str = None, type: str = None) -> List[Dict]:
    """Get COMPREHENSIVE STATISTICAL summary of content presence (10+ metrics).
    
    Returns: total_records, unique_platforms, unique_countries, unique_content, avg/median duration,
    exclusive_count, kids_count, movies_count, series_count.
    Filters: country, platform_name, type.
    Use for detailed analysis. For simple count only, use presence_count instead.
    
    Args:
        country: Country ISO-2 code filter (optional)
        platform_name: Platform name filter (optional)
        type: Content type filter - Movie or Series (optional)
    
    Returns:
        List with comprehensive statistical metrics
    """
    
    filters = {
        "country": country,
        "platform_name": platform_name,
        "type": type
    }
    
    filters = {k: v for k, v in filters.items() if v is not None}

    where_clause, query_params = build_where_clause(filters)
    sql = QUERY_PRESENCE_STATISTICS.format(where_clause=where_clause)

    result = db.execute_query(sql, query_params)
    return result if result else [{"message": "No results found"}]

@tool
def platform_count_by_country(country: str = None) -> List[Dict]:
    """Get QUICK COUNT of streaming platforms by country (lightweight query).
    
    If country (ISO-2) specified: returns platform_count + platforms array for that country.
    If no country: returns platform_count for ALL countries sorted by count.
    Use this for simple platform counting. For detailed statistics including content counts,
    use country_platform_summary instead.
    
    Args:
        country: Country ISO-2 code (optional). If not provided, returns all countries.
    
    Returns:
        List with platform counts by country
    """
    
    if country:
        country_iso = resolve_country_iso(country)
        if not country_iso:
            return [{"message": f"Invalid country code: {country}"}]
            
        sql = QUERY_PLATFORM_COUNT_SPECIFIC_COUNTRY
        country_iso = resolve_country_iso(country_iso)
        query_params = {"country_iso": country_iso}
    else:
        sql = QUERY_PLATFORM_COUNT_ALL_COUNTRIES
        query_params = {}

    result = db.execute_query(sql, query_params)
    return result if result else [{"message": "No results found"}]

@tool
def country_platform_summary(country: str = None) -> List[Dict]:
    """Get COMPREHENSIVE DETAILED summary of platforms and content by country/region (complete analysis).
    
    Returns per country: unique_platforms (count), unique_content (count), total_records,
    movies count, series count, exclusive_content count, and platforms array.
    Supports country/region filtering or global summary.
    Use this for detailed market analysis. For simple platform counting only, use platform_count_by_country instead.
    
    Args:
        country: Country ISO-2 code or region name (optional). If not provided, returns global summary.
    
    Returns:
        List with comprehensive platform and content statistics by country
    """
   
    country_condition = ""
    params = ()
    
    if country:
        isos = resolve_region_isos(country) or [resolve_country_iso(country)]
        isos = [iso for iso in isos if iso]
        
        if isos:
            in_clause, params_list = build_in_clause("p.iso_alpha2", isos)
            country_condition = f"AND {in_clause}"
            params = tuple(params_list)
    
    logger.info(f"Countries: {params}")
    logger.info(f"Country condition: {country_condition}")
    
    sql = QUERY_COUNTRY_PLATFORM_SUMMARY.replace("{country_condition}", country_condition)
    result = db.execute_query(sql, params)
    
    return result if result else [{"message": "No results found"}]