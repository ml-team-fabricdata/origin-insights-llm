# app/modules/countries.py
import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple

from infra.db import run_sql
from infra.config import SETTINGS

__all__ = [
    "COUNTRIES_EN_ES",
    "guess_country",
    "is_country_only_followup",
    "country_pretty_from_iso",
]

try:
    from unidecode import unidecode as _unidecode
except Exception:
    def _unidecode(s):  # type: ignore
        return s


def _clean_text(s: str) -> str:
    s = _unidecode(s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


# ===== Diccionario EN/ES con alias + demonyms =====
COUNTRIES_EN_ES: Dict[str, Dict[str, Any]] = {
    # --- Américas
    "AR":{"en":"Argentina","es":"Argentina","aliases":["arg","argentino","argentina","la argentina"]},
    "US":{"en":"United States","es":"Estados Unidos","aliases":["usa","eeuu","ee uu","u.s.","us","estadounidense","america","ee. uu."]},
    "CA":{"en":"Canada","es":"Canadá","aliases":["canada","canadiense"]},
    "MX":{"en":"Mexico","es":"México","aliases":["mexico","méjico","mex","mexicano","mexicana"]},
    "BR":{"en":"Brazil","es":"Brasil","aliases":["brasil","brazilian","brasileño","brasileña"]},
    "CL":{"en":"Chile","es":"Chile","aliases":["chileno","chilena"]},
    "CO":{"en":"Colombia","es":"Colombia","aliases":["colombiano","colombiana"]},
    "PE":{"en":"Peru","es":"Perú","aliases":["peru","peruano","peruana"]},
    "UY":{"en":"Uruguay","es":"Uruguay","aliases":["uruguayo","uruguaya"]},
    "PY":{"en":"Paraguay","es":"Paraguay","aliases":["paraguayo","paraguaya"]},
    "BO":{"en":"Bolivia","es":"Bolivia","aliases":["boliviano","boliviana"]},
    "EC":{"en":"Ecuador","es":"Ecuador","aliases":["ecuatoriano","ecuatoriana"]},
    "VE":{"en":"Venezuela","es":"Venezuela","aliases":["venezolano","venezolana"]},
    "PR":{"en":"Puerto Rico","es":"Puerto Rico","aliases":["puerto rico","boricua"]},
    "DO":{"en":"Dominican Republic","es":"República Dominicana","aliases":["republica dominicana","dominicano","dominicana"]},
    "CR":{"en":"Costa Rica","es":"Costa Rica","aliases":["costarricense","tico","tica"]},
    "PA":{"en":"Panama","es":"Panamá","aliases":["panama","panameño","panameña"]},
    "SV":{"en":"El Salvador","es":"El Salvador","aliases":["salvadoreño","salvadoreña"]},
    "GT":{"en":"Guatemala","es":"Guatemala","aliases":["guatemalteco","guatemalteca"]},
    "HN":{"en":"Honduras","es":"Honduras","aliases":["hondureño","hondureña"]},
    "NI":{"en":"Nicaragua","es":"Nicaragua","aliases":["nicaragüense","nica"]},
    "CU":{"en":"Cuba","es":"Cuba","aliases":["cubano","cubana"]},
    "HT":{"en":"Haiti","es":"Haití","aliases":["haiti","haitiano","haitiana"]},
    # --- Europa
    "ES":{"en":"Spain","es":"España","aliases":["spain","españa","espanha","español","española"]},
    "PT":{"en":"Portugal","es":"Portugal","aliases":["portugués","portuguesa"]},
    "FR":{"en":"France","es":"Francia","aliases":["francia","francés","francesa"]},
    "DE":{"en":"Germany","es":"Alemania","aliases":["germany","alemania","alemán","alemana","deutschland"]},
    "IT":{"en":"Italy","es":"Italia","aliases":["italia","italiano","italiana"]},
    "GB":{"en":"United Kingdom","es":"Reino Unido","aliases":["uk","u.k.","great britain","gran bretaña","inglaterra","británico","britanico","británica","britanica"]},
    "IE":{"en":"Ireland","es":"Irlanda","aliases":["ireland","irlanda","irlandés","irlandesa"]},
    "NL":{"en":"Netherlands","es":"Países Bajos","aliases":["holland","holanda","neerlandes","neerlandesa","dutch"]},
    "BE":{"en":"Belgium","es":"Bélgica","aliases":["belgica","belga"]},
    "LU":{"en":"Luxembourg","es":"Luxemburgo","aliases":["luxemburgo"]},
    "CH":{"en":"Switzerland","es":"Suiza","aliases":["swiss","suiza","suizo"]},
    "AT":{"en":"Austria","es":"Austria","aliases":["austria","austriaco","austriaca"]},
    "DK":{"en":"Denmark","es":"Dinamarca","aliases":["dinamarca","danés","danesa"]},
    "NO":{"en":"Norway","es":"Noruega","aliases":["noruega","noruego"]},
    "SE":{"en":"Sweden","es":"Suecia","aliases":["suecia","sueco","sueca"]},
    "FI":{"en":"Finland","es":"Finlandia","aliases":["finlandia","finés","finlandés"]},
    "PL":{"en":"Poland","es":"Polonia","aliases":["polonia","polaco","polaca"]},
    "CZ":{"en":"Czechia","es":"Chequia","aliases":["czech republic","república checa","republica checa","checo","checa"]},
    "SK":{"en":"Slovakia","es":"Eslovaquia","aliases":["slovakia","eslovaco","eslovaca"]},
    "HU":{"en":"Hungary","es":"Hungría","aliases":["hungary","hungria","húngaro","húngara"]},
    "RO":{"en":"Romania","es":"Rumanía","aliases":["romania","rumania","rumano","rumana"]},
    "BG":{"en":"Bulgaria","es":"Bulgaria","aliases":["bulgaria","búlgaro","búlgara","bulgaro","bulgara"]},
    "GR":{"en":"Greece","es":"Grecia","aliases":["grecia","griego","griega"]},
    "TR":{"en":"Türkiye","es":"Turquía","aliases":["turkey","turco","turca"]},
    "RU":{"en":"Russia","es":"Rusia","aliases":["rusia","ruso","rusa"]},
    "UA":{"en":"Ukraine","es":"Ucrania","aliases":["ucrania","ucraniano","ucraniana"]},
    "IS":{"en":"Iceland","es":"Islandia","aliases":["islandia","islandés","islandesa"]},
    # --- APAC
    "JP":{"en":"Japan","es":"Japón","aliases":["japon","japonés","japonesa","nipón","nipona"]},
    "KR":{"en":"South Korea","es":"Corea del Sur","aliases":["korea","corea del sur","surcoreano","surcoreana"]},
    "CN":{"en":"China","es":"China","aliases":["china","chino","china continental"]},
    "TW":{"en":"Taiwan","es":"Taiwán","aliases":["taiwan","taiwanés","taiwanesa"]},
    "HK":{"en":"Hong Kong","es":"Hong Kong","aliases":["hong kong","hk"]},
    "SG":{"en":"Singapore","es":"Singapur","aliases":["singapur","singapore"]},
    "TH":{"en":"Thailand","es":"Tailandia","aliases":["tailandia","tailandés","tailandesa"]},
    "VN":{"en":"Vietnam","es":"Vietnam","aliases":["vietnam","vietnamita"]},
    "MY":{"en":"Malaysia","es":"Malasia","aliases":["malasia","malayo","malaya"]},
    "PH":{"en":"Philippines","es":"Filipinas","aliases":["filipinas","filipino","filipina"]},
    "ID":{"en":"Indonesia","es":"Indonesia","aliases":["indonesia","indonesio","indonesia"]},
    "IN":{"en":"India","es":"India","aliases":["india","indio","india"]},
    "PK":{"en":"Pakistan","es":"Pakistán","aliases":["pakistan","paquistaní","paquistani"]},
    "BD":{"en":"Bangladesh","es":"Bangladés","aliases":["bangladesh","bangladesí","bangladesi"]},
    "AU":{"en":"Australia","es":"Australia","aliases":["australia","aussie","australiano","australiana"]},
    "NZ":{"en":"New Zealand","es":"Nueva Zelanda","aliases":["new zealand","nueva zelanda","kiwi"]},
    # --- MENA / África
    "AE":{"en":"United Arab Emirates","es":"Emiratos Árabes Unidos","aliases":["uae","eau","emiratos","dubai","abudhabi","ab u dhabi","abudhābī"]},
    "SA":{"en":"Saudi Arabia","es":"Arabia Saudita","aliases":["arabia saudi","ksa","saudí","saudi"]},
    "QA":{"en":"Qatar","es":"Catar","aliases":["qatar","catar"]},
    "KW":{"en":"Kuwait","es":"Kuwait","aliases":["kuwait"]},
    "BH":{"en":"Bahrain","es":"Baréin","aliases":["bahrein","barhein","baréin","barein"]},
    "OM":{"en":"Oman","es":"Omán","aliases":["oman","omán","mascat"]},
    "IL":{"en":"Israel","es":"Israel","aliases":["israel","israelí","israeli"]},
    "EG":{"en":"Egypt","es":"Egipto","aliases":["egipto","egipcio","egipcia"]},
    "MA":{"en":"Morocco","es":"Marruecos","aliases":["marruecos","marroquí","marroqui"]},
    "DZ":{"en":"Algeria","es":"Argelia","aliases":["argelia","argelino","argelina"]},
    "TN":{"en":"Tunisia","es":"Túnez","aliases":["tunez","tunecino","tunecina"]},
    "ZA":{"en":"South Africa","es":"Sudáfrica","aliases":["sudafrica","sudafricano","sudafricana"]},
    "NG":{"en":"Nigeria","es":"Nigeria","aliases":["nigeria","nigeriano","nigeriana"]},
    "KE":{"en":"Kenya","es":"Kenia","aliases":["kenia","keniano","keniana"]},
    "GH":{"en":"Ghana","es":"Ghana","aliases":["ghana","ghanés","ghanes"]},
    "ET":{"en":"Ethiopia","es":"Etiopía","aliases":["etiopia","etíope","etiope"]},
    # --- Global pseudo-país
    "XX":{"en":"Global","es":"Global","aliases":["global","mundo","world","all"]},
}

_NAME_TO_ISO: Dict[str, str] = {}
for code, meta in COUNTRIES_EN_ES.items():
    en = (meta.get("en") or "")
    es = (meta.get("es") or "")
    aliases = set(meta.get("aliases", []))
    for base in filter(None, [en, es]):
        aliases.add(base)
        aliases.add(base.lower())
        aliases.add(_unidecode(base).lower())
    if en.lower().startswith("united "):
        aliases.add("uk" if code == "GB" else en.replace("United ", "").lower())
    if es.lower() == "reino unido":
        aliases.add("uk")
    for a in aliases:
        _NAME_TO_ISO[_clean_text(a)] = code

_DEMONYMS = {
    "argentino":"AR","argentina":"AR",
    "estadounidense":"US","americano":"US","americana":"US",
    "mexicano":"MX","mexicana":"MX",
    "brasileño":"BR","brasileno":"BR","brasileña":"BR","brasilena":"BR",
    "chileno":"CL","chilena":"CL",
    "colombiano":"CO","colombiana":"CO",
    "peruano":"PE","peruana":"PE",
    "español":"ES","espanol":"ES","española":"ES","espanola":"ES",
    "británico":"GB","britanico":"GB","británica":"GB","britanica":"GB",
    "alemán":"DE","aleman":"DE","alemana":"DE",
    "francés":"FR","frances":"FR","francesa":"FR",
    "italiano":"IT","italiana":"IT",
    "canadiense":"CA",
    "japonés":"JP","japones":"JP","japonesa":"JP",
    "coreano":"KR","coreana":"KR",
    "chino":"CN","china":"CN",
    "indio":"IN","india":"IN",
    "australiano":"AU","australiana":"AU",
}


def _deterministic_country_resolver(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    Resolver rápido por diccionario: nombres/alias/gentilicios y códigos explícitos.
    """
    t = _clean_text(text)
    raw = text or ""

    # CÓDIGO explícito solo si viene con prefijo (country|país|iso2|code)
    m = re.search(r'(?i)\b(?:country|pa[ií]s|pais|iso2|code)\s*[:=]\s*([A-Z]{2}|UK|XX)\b', raw)
    if m:
        code = m.group(1).upper()
        if code == "UK":
            code = "GB"
        if code in COUNTRIES_EN_ES:
            meta = COUNTRIES_EN_ES[code]
            pretty = meta.get("es") or meta.get("en") or code
            return code, pretty, 0.96
        if code == "XX":
            return "XX", COUNTRIES_EN_ES["XX"]["es"], 0.90

    # Nombre / alias directo
    for name, iso in _NAME_TO_ISO.items():
        if re.search(rf"\b{re.escape(name)}\b", t):
            meta = COUNTRIES_EN_ES.get(iso, {})
            pretty = meta.get("es") or meta.get("en") or name.title()
            return iso, pretty, 0.95

    # Gentilicios
    for dem, iso in _DEMONYMS.items():
        if re.search(rf"\b{re.escape(_clean_text(dem))}\b", t):
            meta = COUNTRIES_EN_ES.get(iso, {})
            pretty = meta.get("es") or meta.get("en") or iso
            return iso, pretty, 0.88

    # Abreviaturas comunes exactas
    if t in {"eeuu", "ee uu", "u s a", "u.s.", "u.k."}:
        iso = "GB" if t == "u.k." else "US"
        meta = COUNTRIES_EN_ES.get(iso, {})
        return iso, (meta.get("es") or meta.get("en") or iso), 0.88

    return None, None, 0.0


# ===== Cache desde DB =====
_COUNTRY_CACHE = {"code_to_name": {}, "name_to_code": {}, "aliases": {}}
_COUNTRY_LOADED = False


def _norm(s: str) -> str:
    return _clean_text(s)


def _load_from_countries_table() -> int:
    rows = run_sql("SELECT name, iso_alpha2 FROM ms.countries;")
    count = 0
    for r in rows:
        code = (r.get("iso_alpha2") or "").strip().upper()
        name = (r.get("name") or "").strip()
        if not code or not name:
            continue
        _COUNTRY_CACHE["code_to_name"][code] = name
        _COUNTRY_CACHE["name_to_code"][_norm(name)] = code
        count += 1
    return count


def _load_from_presence_distinct() -> int:
    count = 0
    try:
        rows = run_sql("""
            SELECT DISTINCT UPPER(COALESCE(country_iso2, iso_alpha2)) AS code
            FROM ms.new_cp_presence
            WHERE COALESCE(country_iso2, iso_alpha2) ~ '^[A-Za-z]{2}$'
        """)
        for r in rows:
            code = (r.get("code") or "").strip().upper()
            if not code:
                continue
            _COUNTRY_CACHE["code_to_name"].setdefault(code, code)
            _COUNTRY_CACHE["name_to_code"].setdefault(_norm(code), code)
            count += 1
    except Exception:
        pass
    try:
        rows = run_sql("""
            SELECT DISTINCT platform_country AS name
            FROM ms.new_cp_presence
            WHERE platform_country IS NOT NULL AND LENGTH(TRIM(platform_country)) > 0
        """)
        for r in rows:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            _COUNTRY_CACHE["name_to_code"].setdefault(_norm(name), name)
            _COUNTRY_CACHE["code_to_name"].setdefault(name, name)
            count += 1
    except Exception:
        pass
    return count


def _seed_aliases():
    alias = _COUNTRY_CACHE["aliases"]

    def a(keys, code):
        for k in keys:
            alias[_norm(k)] = code

    a(["Estados Unidos", "EEUU", "EE. UU.", "USA", "U.S.", "United States", "United States of America", "US"], "US")
    a(["Reino Unido", "UK", "U.K.", "United Kingdom", "Great Britain", "Britain"], "GB")
    alias[_norm("España")] = "ES"
    alias[_norm("Spanish")] = "ES"
    for k in ["Global", "Mundo", "World", "XX"]:
        alias[_norm(k)] = "XX"


def _load_countries_cache(force: bool = False):
    global _COUNTRY_LOADED
    if not force and _COUNTRY_LOADED and len(_COUNTRY_CACHE["code_to_name"]) >= 10:
        return
    _COUNTRY_CACHE["code_to_name"].clear()
    _COUNTRY_CACHE["name_to_code"].clear()
    _COUNTRY_CACHE["aliases"].clear()
    loaded = 0
    try:
        loaded = _load_from_countries_table()
    except Exception:
        loaded = 0
    if loaded < 10:
        try:
            loaded += _load_from_presence_distinct()
        except Exception:
            pass
    _seed_aliases()
    _COUNTRY_LOADED = loaded >= 10


def _db_country_resolver(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    _load_countries_cache()
    s_norm = _norm(text)
    raw = (text or "").strip()

    # CÓDIGO explícito con prefijo
    m = re.search(r'(?i)\b(?:country|pa[ií]s|pais|iso2|code)\s*[:=]\s*([A-Z]{2}|UK|XX)\b', raw)
    if m:
        code = m.group(1).upper()
        if code == "UK":
            code = "GB"
        if code in _COUNTRY_CACHE["code_to_name"]:
            return code, _COUNTRY_CACHE["code_to_name"][code]
        if code == "XX":
            return "XX", "Global"

    # Alias / nombre exacto
    if s_norm in _COUNTRY_CACHE["aliases"]:
        code = _COUNTRY_CACHE["aliases"][s_norm]
        pretty = _COUNTRY_CACHE["code_to_name"].get(code, "Global" if code == "XX" else code)
        return code, pretty
    if s_norm in _COUNTRY_CACHE["name_to_code"]:
        code = _COUNTRY_CACHE["name_to_code"][s_norm]
        return code, _COUNTRY_CACHE["code_to_name"].get(code, code)

    # Fuzzy ms.countries (con unaccent si existe)
    try:
        rows = run_sql("""
            WITH cand AS (
              SELECT iso_alpha2 AS code, name, similarity(name, %(q)s) AS s1
              FROM ms.countries
              WHERE name %% %(q)s
              ORDER BY s1 DESC
              LIMIT 1
            )
            SELECT * FROM cand;
        """, {"q": raw})
        if rows:
            code = (rows[0].get("code") or "").upper()
            if code:
                return code, rows[0].get("name") or code
    except Exception:
        pass
    try:
        rows = run_sql("""
            WITH cand AS (
              SELECT iso_alpha2 AS code, name,
                     GREATEST(similarity(name, %(q)s),
                              similarity(unaccent(name), unaccent(%(q)s))) AS s
              FROM ms.countries
              WHERE name %% %(q)s
                 OR unaccent(name) %% unaccent(%(q)s)
              ORDER BY s DESC
              LIMIT 1
            )
            SELECT * FROM cand;
        """, {"q": raw})
        if rows:
            code = (rows[0].get("code") or "").upper()
            if code:
                return code, rows[0].get("name") or code
    except Exception:
        pass

    # Nombre corto → usar tal cual para filtrar por platform_country si hace falta
    name_tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", raw)
    if 1 <= len(name_tokens) <= 3:
        pretty = " ".join(name_tokens).strip()
        if pretty:
            return pretty, pretty

    return None, None


def _llm_country_extract(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """
    Extractor LLM opcional (Claude 3.5 Haiku u otro vía infra.bedrock).
    Reglas:
      - No confundas la preposición inglesa 'in' como país India (IN) salvo que el contexto lo haga inequívoco.
      - Normaliza UK→GB, Global/World→XX.
      - Si no hay país inequívoco: code=null, confidence<=0.5.
    """
    if not SETTINGS.enable_llm_country:
        return None, None, 0.0
    try:
        # “in” suelto para evitar falso positivo India
        if re.fullmatch(r"\s*in\s*", str(text or ""), flags=re.I):
            return None, None, 0.0

        from infra.bedrock import call_bedrock_llm1  # wrapper rápido
        prompt = (
            "Eres un extractor de países para disponibilidad/mercado de streaming.\n"
            "Devuelve SOLO JSON válido: {\"code\":\"ISO2 o null\",\"name\":\"ES/EN o null\",\"confidence\":0..1}\n"
            "Reglas:\n"
            "1) Si no hay país inequívoco, usa code=null y confidence<=0.5.\n"
            "2) NO confundas la preposición inglesa 'in' (conector) con India (IN).\n"
            "   Si el texto nombra India explícitamente ('India', 'en India') o usa 'IN' como ISO separado\n"
            "   (ej.: 'in, IN?' o 'in IN?'), entonces sí es India.\n"
            "3) Acepta alias: EEUU/USA/U.S.→US, UK→GB, Reino Unido→GB; Global/World→XX.\n"
            "4) ISO2 en mayúsculas.\n"
            f"Texto: {text}\n"
            "Respuesta JSON:"
        )
        r = call_bedrock_llm1(prompt) or {}
        content = (r.get("completion") or "").strip()
        m = re.search(r"\{.*\}", content, flags=re.S)
        if not m:
            return None, None, 0.0
        js = json.loads(m.group(0))
        code = (js.get("code") or None)
        name = js.get("name") or None
        conf = float(js.get("confidence") or 0.0)

        if code:
            code = code.upper().strip()
            if code == "UK":
                code = "GB"
            if code == "XX":
                return "XX", (COUNTRIES_EN_ES.get("XX", {}).get("es") or "Global"), max(conf, 0.6)
            if code in COUNTRIES_EN_ES:
                pretty = COUNTRIES_EN_ES[code].get("es") or COUNTRIES_EN_ES[code].get("en") or name
                return code, pretty, max(conf, 0.6)

        # Si no hubo code pero hay name → diccionario determinista
        if name:
            iso = _NAME_TO_ISO.get(_clean_text(name))
            if iso:
                pretty = COUNTRIES_EN_ES[iso].get("es") or COUNTRIES_EN_ES[iso].get("en") or name
                return iso, pretty, max(conf, 0.55)

        return None, None, conf
    except Exception:
        return None, None, 0.0


def guess_country(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Entrada pública:
      1) Resolver determinista (alias/gentilicios/código) →
      2) Cache/DB (countries/presence con fuzzy) →
      3) LLM (si ENABLE_LLM_COUNTRY=1).
    Devuelve (ISO2|nombre_liberal, pretty_name).
    """
    iso, pretty, _ = _deterministic_country_resolver(text)
    if iso:
        return iso, pretty
    iso, pretty = _db_country_resolver(text)
    if iso:
        return iso, pretty
    iso, pretty, _ = _llm_country_extract(text)
    return iso, pretty


def is_country_only_followup(text: str) -> bool:
    """
    Detecta follow-ups del tipo “¿y en {país}?” / “and in {country}?”.
    Valida con guess_country para evitar falsos positivos.
    """
    if not text:
        return False
    s = _clean_text(text)
    if re.search(r"\b(y|and)\s+en?\s+", s):
        iso2, pretty = guess_country(text)
        return bool(iso2 or pretty)
    return False


def country_pretty_from_iso(code: Optional[str]) -> Optional[str]:
    """
    Devuelve nombre bonito desde ISO2 usando cache/DB si es posible.
    """
    if not code:
        return None
    try:
        _load_countries_cache()
        return _COUNTRY_CACHE["code_to_name"].get(str(code).upper())
    except Exception:
        return None