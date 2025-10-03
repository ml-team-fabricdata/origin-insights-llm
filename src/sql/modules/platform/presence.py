from src.sql.utils.constants_sql import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.default_import import *
from src.sql.queries.platform.queries_presence import *
from src.sql.utils.validators_shared import *

def build_where_clause(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Build WHERE clause and parameters from filters"""
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
        country_iso = resolve_country_iso(filters["country"])
        if country_iso:
            conditions.append("p.iso_alpha2 = %(country_iso)s")
            params["country_iso"] = country_iso.upper()

    if filters.get("platform_name"):
        platform = resolve_platform_name(filters["platform_name"])
        if platform:
            conditions.append("p.platform_name = %(platform_name)s")
            params["platform_name"] = platform

    if filters.get("platform_code"):
        conditions.append("p.platform_code = %(platform_code)s")
        params["platform_code"] = filters["platform_code"]

    if filters.get("type"):
        content_type = resolve_content_type(filters["type"])
        if content_type:
            conditions.append("p.type = %(type)s")
            params["type"] = content_type

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

def presence_count(country: str = None, platform_name: str = None, uid: str = None, 
                  type: str = None, title_like: str = None) -> List[Dict]:
    """Count presence records with optional filters"""
    
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

def presence_list(country: str = None, platform_name: str = None, type: str = None,
                 title_like: str = None, limit: int = 25, offset: int = 0,
                 order_by: str = "clean_title", order_dir: str = "ASC") -> List[Dict]:
    """List presence records with pagination and filtering"""
    
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

def presence_distinct(column: str, country: str = None, platform_name: str = None,
                     type: str = None, limit: int = 100) -> List[Dict]:
    """Get distinct values from content presence table columns"""
    
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

def presence_statistics(country: str = None, platform_name: str = None, type: str = None) -> List[Dict]:
    """Get statistical summary of presence data"""
    
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

def platform_count_by_country(country: str = None) -> List[Dict]:
    """Get count of platforms by country or for a specific country"""
    
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

def country_platform_summary(country: str = None) -> List[Dict]:
    """Get summary statistics of platforms and content by country or region"""
   
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