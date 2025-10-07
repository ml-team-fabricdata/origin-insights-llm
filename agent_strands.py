import os
from typing import Optional, List, Union, Dict, Any
from strands import Agent, tool

# Importar funciones reales de los módulos de negocio
import src.sql.modules.business.pricing as pr
import src.sql.modules.business.intelligence as intel

# ---------- HERRAMIENTAS: PRICING ----------
# (Las definiciones de las herramientas: prices_latest, prices_history, 
# prices_changes_last_n_days, prices_stats, hits_with_quality 
# permanecen sin cambios)

@tool
def prices_latest(uid: Optional[str] = None, country: Optional[str] = None, platform_name: Optional[str] = None, platform_code: Optional[str] = None, price_type: Optional[Union[str, List[str]]] = None, definition: Optional[List[str]] = None, license_: Optional[List[str]] = None, currency: Optional[Union[str, List[str]]] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, limit: int = 50) -> List[Dict[str, Any]]:
    return pr.tool_prices_latest(uid=uid, country=country, platform_name=platform_name, platform_code=platform_code, price_type=price_type, definition=definition, license_=license_, currency=currency, min_price=min_price, max_price=max_price, limit=limit)

@tool
def prices_history(hash_unique: Optional[str] = None, uid: Optional[str] = None, title_like: Optional[str] = None, country: Optional[str] = None, platform_name: Optional[str] = None, platform_code: Optional[str] = None, price_type: Optional[Union[str, List[str]]] = None, definition: Optional[List[str]] = None, license_: Optional[List[str]] = None, currency: Optional[Union[str, List[str]]] = None, min_price: Optional[float] = None, max_price: Optional[float] = None, limit: int = 500) -> List[Dict[str, Any]]:
    return pr.tool_prices_history(hash_unique=hash_unique, uid=uid, title_like=title_like, country=country, platform_name=platform_name, platform_code=platform_code, price_type=price_type, definition=definition, license_=license_, currency=currency, min_price=min_price, max_price=max_price, limit=limit)

@tool
def prices_changes_last_n_days(n_days: int = 7, hash_unique: Optional[str] = None, uid: Optional[str] = None, country: Optional[str] = None, platform_code: Optional[str] = None, price_type: Optional[Union[str, List[str]]] = None, direction: str = "down", limit: int = 200) -> List[Dict[str, Any]]:
    return pr.tool_prices_changes_last_n_days(n_days=n_days, hash_unique=hash_unique, uid=uid, country=country, platform_code=platform_code, price_type=price_type, direction=direction, limit=limit)

@tool
def prices_stats(country: Optional[str] = None, platform_name: Optional[str] = None, platform_code: Optional[str] = None, price_type: Optional[Union[str, List[str]]] = None, definition: Optional[List[str]] = None, license_: Optional[List[str]] = None, currency: Optional[Union[str, List[str]]] = None) -> List[Dict[str, Any]]:
    return pr.tool_prices_stats(country=country, platform_name=platform_name, platform_code=platform_code, price_type=price_type, definition=definition, license_=license_, currency=currency)

@tool
def hits_with_quality(uid: str, country: Optional[str] = None, definition: Optional[List[str]] = None, license_: Optional[List[str]] = None, limit: int = 50, scoped_by_country: bool = True, fallback_when_empty: bool = True) -> List[Dict[str, Any]]:
    return pr.tool_hits_with_quality(uid=uid, country_input=country, definition=definition, license_=license_, limit=limit, scoped_by_country=scoped_by_country, fallback_when_empty=fallback_when_empty)


# ---------- HERRAMIENTAS: INTELLIGENCE ----------
# (Las definiciones de las herramientas: get_platform_exclusivity_by_country,
# catalog_similarity_for_platform, titles_in_A_not_in_B
# permanecen sin cambios)
@tool
def get_platform_exclusivity_by_country(platform_name: str, country: str, limit: int = 100) -> List[Dict]:
    return intel.get_platform_exclusivity_by_country(platform_name=platform_name, country=country, limit=limit)

@tool
def catalog_similarity_for_platform(platform: str, iso_a: str, iso_b: str, combined_format: Optional[str] = None) -> Dict[str, Any]:
    return intel.catalog_similarity_for_platform(platform=platform, iso_a=iso_a, iso_b=iso_b, __arg1=combined_format)

@tool
def titles_in_A_not_in_B(country_in: str, country_not_in: str, platform: Optional[str] = None, limit: int = 50) -> List[Dict]:
    return intel.titles_in_A_not_in_B_sql(country_in=country_in, country_not_in=country_not_in, platform=platform, limit=limit)


# ---------- Configuración del Modelo y Agentes ----------

_MODEL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

# Agente especializado en precios con su conjunto completo de herramientas
PRICING_AGENT = Agent(
    model=_MODEL,
    tools=[prices_latest, prices_history, prices_changes_last_n_days, prices_stats, hits_with_quality],
    system_prompt=(
        "Eres un analista experto en precios de catálogos de streaming. "
        "Tu tarea es responder a las preguntas del usuario utilizando las herramientas de precios a tu disposición. "
        "Analiza la pregunta, selecciona la mejor herramienta (o herramientas) y proporciona una respuesta clara y concisa basada en los datos obtenidos. "
        "Explica brevemente los filtros aplicados y presenta los datos en un formato JSON legible."
    ),
)

# Agente especializado en inteligencia de catálogo con su conjunto completo de herramientas
INTELLIGENCE_AGENT = Agent(
    model=_MODEL,
    tools=[get_platform_exclusivity_by_country, catalog_similarity_for_platform, titles_in_A_not_in_B],
    system_prompt=(
        "Eres un analista experto en inteligencia de catálogos de streaming. "
        "Tu tarea es responder a las preguntas del usuario sobre exclusividad, similitud y diferencias de catálogos entre países o plataformas. "
        "Utiliza las herramientas de inteligencia para obtener los datos necesarios y presenta una respuesta clara y concisa. "
        "Resume los hallazgos y presenta los datos en un formato JSON legible."
    ),
)

# Un agente general que puede usarse como fallback o para tareas que no encajan claramente
GENERAL_AGENT = Agent(
    model=_MODEL,
    tools=[prices_latest, prices_history, prices_changes_last_n_days, prices_stats, hits_with_quality, get_platform_exclusivity_by_country, catalog_similarity_for_platform, titles_in_A_not_in_B],
    system_prompt=(
        "Eres un analista experto en catálogos y precios de streaming. "
        "Tienes acceso a herramientas de precios e inteligencia. "
        "Analiza la pregunta del usuario y utiliza las herramientas adecuadas para dar una respuesta completa y precisa. "
        "Explica tus hallazgos y formatea la salida en JSON."
    ),
)