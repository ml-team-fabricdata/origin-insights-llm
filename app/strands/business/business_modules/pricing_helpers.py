"""Pricing Module Helpers

Helper functions for pricing operations:
- Parameter normalization
- ID detection and resolution
- Query building utilities
"""

from typing import List, Optional, Tuple, Literal
from app.strands.infrastructure.database.utils import db
from app.strands.infrastructure.database.constants import PRICES_TBL, PRES_TBL
from app.strands.infrastructure.validators.shared import (
    resolve_country_iso,
    resolve_platform_name,
    validate_limit,
    validate_days_back
)
from app.strands.business.business_queries.pricing_queries import (
    SQL_GET_HASHES_BY_UID,
    SQL_DETECT_HASH_EXISTS,
    SQL_DETECT_UID_EXISTS
)
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Type Definitions
# =============================================================================

IdKind = Literal["hash_unique", "uid", "none", "both"]

# =============================================================================
# Normalization Helpers
# =============================================================================

def _norm(s: str) -> str:
    """Normalize string to lowercase."""
    return (s or "").strip().lower()


def normalize_tool_call(args, kwargs):
    """
    Tolerancia a llamadas posicionales del orquestador:
    - (dict)           → merge con kwargs
    - (str/int/...)    → mapea a '__arg1'
    - >1 posicionales  → toma el primero como '__arg1'
    """
    if args:
        if len(args) == 1:
            a0 = args[0]
            if isinstance(a0, dict):
                merged = dict(a0)
                merged.update(kwargs or {})
                return merged
            merged = dict(kwargs or {})
            merged.setdefault("__arg1", a0)
            return merged
        merged = dict(kwargs or {})
        merged.setdefault("__arg1", args[0])
        return merged
    return kwargs or {}


def resolve_definition(values: Optional[List[str]]) -> Optional[List[str]]:
    """Normalize and validate video definitions."""
    from app.strands.infrastructure.validators.shared import DEF_ALIASES, VALID_DEFINITIONS
    
    if not values:
        return None
    
    resolved: List[str] = []
    for value in values:
        key = _norm(value)
        canonical = DEF_ALIASES.get(key)
        if not canonical:
            upper_val = value.strip().upper()
            canonical = upper_val.replace(" ", "")
            if canonical == "SDHD":
                canonical = "SD/HD"
        if canonical and canonical in VALID_DEFINITIONS:
            resolved.append(canonical)
        else:
            logger.warning(f"Invalid definition ignored: {value}")
    
    return resolved or None


def resolve_license(values: Optional[List[str]]) -> Optional[List[str]]:
    """Normalize and validate license types."""
    from app.strands.infrastructure.validators.shared import LIC_ALIASES, VALID_LICENSES
    
    if not values:
        return None
    
    resolved: List[str] = []
    for value in values:
        key = _norm(value)
        canonical = LIC_ALIASES.get(key, value.strip().upper())
        if canonical in VALID_LICENSES:
            resolved.append(canonical)
        else:
            logger.warning(f"Invalid license ignored: {value}")
    
    return resolved or None

# =============================================================================
# ID Detection and Resolution
# =============================================================================

def detect_id_kind(value: str) -> Tuple[IdKind, Optional[str]]:
    """
    Consulta la DB para ver si 'value' existe como hash_unique (prices) o uid (presence).
    
    Returns:
        Tuple of (kind, value) where kind is one of: hash_unique, uid, both, none
    """
    if not value:
        return "none", None

    exists_hash = bool(db.execute_query(SQL_DETECT_HASH_EXISTS, (value,)))
    exists_uid = bool(db.execute_query(SQL_DETECT_UID_EXISTS, (value,)))

    if exists_hash and exists_uid:
        return "both", value
    if exists_hash:
        return "hash_unique", value
    if exists_uid:
        return "uid", value
    return "none", None


def get_hashes_by_uid(
    uid: str, 
    *, 
    iso: Optional[str] = None, 
    platform_name: Optional[str] = None
) -> List[str]:
    """
    Devuelve DISTINCT hash_unique desde presence para un uid, 
    con filtros opcionales por país/plataforma.
    
    Args:
        uid: Content unique identifier
        iso: Country ISO-2 code (optional)
        platform_name: Platform name (optional)
        
    Returns:
        List of hash_unique values
    """
    if not uid:
        return []
    
    where, params = ["p.uid = %s"], [uid]
    
    if iso:
        where.append("LOWER(p.iso_alpha2) = %s")
        params.append(iso.lower())
    
    if platform_name:
        where.append("LOWER(p.platform_name) = %s")
        params.append(platform_name.lower())
    
    sql = SQL_GET_HASHES_BY_UID.replace(
        "{WHERE_CONDITIONS}", 
        " AND ".join(where)
    )
    
    rows = db.execute_query(sql, tuple(params)) or []
    return [r["hash_unique"] for r in rows if r.get("hash_unique")]


def get_hash_by_uid(
    uid: str, 
    *, 
    iso: Optional[str] = None, 
    platform_name: Optional[str] = None
) -> Optional[str]:
    """
    Variante que devuelve un solo hash (primero disponible).
    
    Args:
        uid: Content unique identifier
        iso: Country ISO-2 code (optional)
        platform_name: Platform name (optional)
        
    Returns:
        First hash_unique found or None
    """
    lst = get_hashes_by_uid(uid, iso=iso, platform_name=platform_name)
    return lst[0] if lst else None

# =============================================================================
# Query Building Helpers
# =============================================================================

def build_join_presence(need_presence: bool) -> str:
    """Build JOIN clause for presence table if needed."""
    if need_presence:
        return f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique"
    return ""


def build_where_scopes(scopes: List[str]) -> str:
    """Build WHERE clause from list of conditions."""
    if scopes:
        return "WHERE " + " AND ".join(scopes)
    return ""


def build_in_clause(column: str, values: List[str]) -> str:
    """Build IN clause for SQL query."""
    if not values:
        return ""
    placeholders = ', '.join(['%s'] * len(values))
    return f"{column} IN ({placeholders})"
