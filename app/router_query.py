# app/router_query.py
import os
import re
import json
import logging
from uuid import uuid4
from functools import lru_cache
from typing import Optional, List, Dict, Any, Tuple, Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.modules import titles as m_titles
from app.modules import countries as m_countries
from app.modules import metadata as m_meta
from app.modules import availability as m_avail
from app.modules import hits as m_hits

log = logging.getLogger("router_query")
router = APIRouter()

# ===================== Modelos de I/O (contrato del HTML) =====================
class Candidate(BaseModel):
    uid: str
    imdb_id: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    type: Optional[str] = None
    directors: Optional[str] = None
    sim: Optional[float] = None

class NextAction(BaseModel):
    type: Literal["select_candidate", "none"] = "none"
    method: Literal["POST", "GET"] = "POST"
    endpoint: str = "/query"

class QueryIn(BaseModel):
    session_id: Optional[str] = None
    message: str
    language: Optional[str] = None     # hint del front
    select_uid: Optional[str] = None
    select_imdb_id: Optional[str] = None
    context_uid: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None

class QueryOut(BaseModel):
    session_id: str
    step: Literal["answer", "disambiguation", "error"]
    text: str
    candidates: List[Candidate] = Field(default_factory=list)
    next: Optional[NextAction] = None
    selected_uid: Optional[str] = None

# ===================== Sesiones (memoria/Redis) =====================
SESS_TTL = int(os.getenv("SESS_TTL", "3600"))
_R = None
try:
    import redis  # type: ignore
    if os.getenv("REDIS_URL"):
        _R = redis.from_url(os.getenv("REDIS_URL"))
        log.info("Redis session store enabled.")
except Exception as e:
    log.info("Redis not enabled: %s", e)

def _default_ctx() -> Dict[str, Any]:
    return {
        "last_uid": None,
        "last_imdb_id": None,
        "last_title": None,
        "last_year": None,
        "last_candidates": [],
        "last_country": None,
        "last_term": None,
    }

_MEM: Dict[str, Dict[str, Any]] = {}

def _sess_get(sid: str) -> Dict[str, Any]:
    if _R:
        raw = _R.get(f"sess:{sid}")
        if raw:
            try: return json.loads(raw)
            except: pass
        ctx = _default_ctx()
        _R.setex(f"sess:{sid}", SESS_TTL, json.dumps(ctx))
        return ctx
    if sid not in _MEM:
        _MEM[sid] = _default_ctx()
    return _MEM[sid]

def _sess_set(sid: str, ctx: Dict[str, Any]) -> None:
    if _R:
        _R.setex(f"sess:{sid}", SESS_TTL, json.dumps(ctx))
    else:
        _MEM[sid] = ctx

def _ensure_session(session_id: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    sid = session_id or uuid4().hex
    return sid, _sess_get(sid)

# ===================== Idioma: detección + traducción =====================
try:
    from langdetect import detect as _ld_detect
except Exception:
    _ld_detect = None

RE_ES_HINT = re.compile(r"[¿¡áéíóúñ]|\b(cu[aá]l|qu[eé]|d[oó]nde|pel[ií]cula|serie|ver|plataforma)\b", re.I)
RE_EN_HINT = re.compile(r"\b(what|where|movie|series|watch|platform)\b", re.I)

def _explicit_lang(msg: str) -> Optional[str]:
    s = (msg or "").lower()
    if "en español" in s or "responde en español" in s or "reply in spanish" in s:
        return "es"
    if "in english" in s or "reply in english" in s or "answer in english" in s:
        return "en"
    return None

def _detect_lang_local(text: str, fallback="es") -> str:
    try:
        if _ld_detect:
            return (_ld_detect(text or "") or fallback).split("-")[0]
    except Exception:
        pass
    t = (text or "").lower()
    if RE_ES_HINT.search(t): return "es"
    if RE_EN_HINT.search(t): return "en"
    return fallback

def _detect_lang_llm(text: str, fallback: str) -> str:
    try:
        if os.getenv("ENABLE_LLM_LANG", "0") != "1":
            return fallback
        from infra.bedrock import call_bedrock_llm1  # lazy
        prompt = (
            "Clasifica el idioma del siguiente texto SOLO como \"es\" o \"en\".\n"
            "Responde con una sola palabra (es|en), sin explicaciones.\n\n"
            f"Texto:\n{text}"
        )
        r = call_bedrock_llm1(prompt) or {}
        out = (r.get("completion") or "").strip().lower()
        return "es" if out.startswith("es") else ("en" if out.startswith("en") else fallback)
    except Exception:
        return fallback

def detect_user_lang(message: str, hint: Optional[str]) -> str:
    explicit = _explicit_lang(message)
    if explicit: return explicit
    local = _detect_lang_local(message, fallback=(hint or "es"))
    return _detect_lang_llm(message, fallback=local)

def _i18n(es: str, en: str, lang: str) -> str:
    return es if (lang or "es").startswith("es") else en

def _translate_with_llm(text: str, target_lang: str) -> str:
    try:
        if not text or os.getenv("ENABLE_TRANSLATION", "1") != "1":
            return text
        from infra.bedrock import call_bedrock_llm1  # lazy
        to = "Spanish" if target_lang.startswith("es") else "English"
        prompt = (
            f"Traduce al {to} el siguiente texto. Mantén nombres propios y URLs.\n"
            "Devuelve SOLO el texto traducido, sin comillas ni notas.\n\n"
            f"Texto:\n{text}"
        )
        r = call_bedrock_llm1(prompt) or {}
        out = (r.get("completion") or "").strip()
        return out or text
    except Exception:
        return text

def translate_if_needed(text: str, target_lang: str) -> str:
    if not text or target_lang not in ("es", "en"):
        return text
    src = None
    try:
        if _ld_detect:
            src = (_ld_detect(text or "") or "").split("-")[0]
    except Exception:
        src = None
    if src and src.startswith(target_lang):
        return text
    if target_lang == "es":
        return _translate_with_llm(text, "es")
    if target_lang == "en":
        return _translate_with_llm(text, "en")
    return text

# ===================== Heurísticas / regex auxiliares =====================
RE_SYNOPSIS = re.compile(r"\b(de\s*qu[eé]\s*trata|sinopsis|plot|summary|synopsis)\b", re.I)
RE_AVAIL = re.compile(r"\b(d[oó]nde.*(?:ver|verla|verlo)|where.*watch|availability|available|plataforma|precio[s]?)\b", re.I)
RE_HITS = re.compile(r"\b(hits|popularidad|popularity|top\s*\d+|m[aá]s\s+popular(?:es)?|most\s+popular)\b", re.I)

RE_GREET = re.compile(r"^\s*(hola|buen[oa]s|hi|hello|hey)\b", re.I)
RE_IDENTITY = re.compile(r"(qu[ié]n eres|qu[eé] eres|who are you|what are you)", re.I)

def _is_global_hits_query(msg: str) -> bool:
    s = (msg or "").lower()
    if re.search(r"\b(m[aá]s\s+popular(?:es)?|most\s+popular|top\s*\d+)\b", s):
        if not re.search(r"[\"“”‘’']", s) and not re.search(r"\b(este|esta|this)\b", s):
            return True
    return False

@lru_cache(maxsize=1024)
def _cache_search(term: str, min_sim: float, top_k: int):
    rows = m_titles.search_title_candidates(term, top_k=top_k, min_similarity=min_sim) or []
    seen, out = set(), []
    for r in rows:
        key = (r.get("imdb_id") or r.get("uid") or "").lower()
        if key and key not in seen:
            out.append(r); seen.add(key)
    return tuple(out[:10])

def _search_candidates_from_text(text: str, min_sim: float = None, top_k: int = None) -> List[Candidate]:
    term = (m_titles.extract_title_query(text, guess_country_fn=m_countries.guess_country) or text or "").strip().lower()
    if not term:
        return []
    ms = float(min_sim if min_sim is not None else float(os.getenv("MIN_SIMILARITY", "0.80")))
    tk = int(top_k if top_k is not None else int(os.getenv("TOP_K", "20")))
    try:
        rows = list(_cache_search(term, ms, tk))
    except Exception:
        rows = m_titles.search_title_candidates(term, top_k=tk, min_similarity=ms) or []
    return [Candidate(**r) for r in rows]

def _safe_autopick(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows: return None
    s0 = float(rows[0].get("sim") or 0.0)
    s1 = float(rows[1].get("sim") or 0.0) if len(rows) > 1 else 0.0
    SIM = float(os.getenv("AUTOPICK_SIM", "0.94"))
    DEL = float(os.getenv("AUTOPICK_DELTA", "0.03"))
    if s0 >= SIM and (s0 - s1) >= DEL: return rows[0]
    return None

def _spanish_kind(t: Optional[str]) -> str:
    t = (t or "").lower()
    return "película" if t == "movie" else ("serie" if t == "series" else "título")

def _format_candidates_list(cands: List[Candidate]) -> str:
    out = []
    for i, c in enumerate(cands, start=1):
        y = c.year if c.year is not None else "s/f"
        imdb = c.imdb_id or "-"
        out.append(f"{i}. {c.title} ({y}) — UID: {c.uid} — IMDb: {imdb}")
    return "\n".join(out)

def _disambig_text(lang: str) -> str:
    return _i18n(
        "Encontré varios contenidos con ese título, ¿puedes indicarme si te refieres a alguno de estos?\n\n"
        "(puedes indicarme el número, decirme «el primero» o proveer el año o UID o IMDb).",
        "I found multiple titles with that name—tell me which one you mean:\n\n"
        "(you can reply with the number, say “the first”, or provide the year, UID, or IMDb).",
        lang,
    )

def _format_selected_metadata(meta: Dict[str, Any], lang: str) -> str:
    t = meta.get("title") or "(título)"
    y = meta.get("year")
    kind = _spanish_kind(meta.get("type")) if lang.startswith("es") else (meta.get("type") or "title")
    dir_ = meta.get("directors")
    syn_raw = meta.get("synopsis") or (_i18n("Sin sinopsis disponible.", "No synopsis available.", lang))
    syn = translate_if_needed(syn_raw, lang)  # Traducción aquí
    uid = meta.get("uid") or "-"
    imdb = meta.get("imdb_id") or "-"
    if lang.startswith("es"):
        header = f"{t}: es una {kind}{f' de {y}' if y else ''}"
        if dir_: header += f", dirigida por {dir_}"
        body = f"Sinopsis: {syn}"
        tail = f"(UID: {uid} — IMDb: {imdb})\n\n¿Quieres disponibilidad por plataforma/país o popularidad (HITS) en algún mercado u otro dato?"
        return f"{header}. {body}\n{tail}"
    else:
        header = f"{t}: a {kind}{f' from {y}' if y else ''}"
        if dir_: header += f", directed by {dir_}"
        body = f"Synopsis: {syn}"
        tail = f"(UID: {uid} — IMDb: {imdb})\n\nWould you like availability by platform/country or popularity (HITS) in any market?"
        return f"{header}. {body}\n{tail}"

# --- Selección por número/ordinal/UID/IMDb ---
_ORD_MAP = {
    "1":1,"2":2,"3":3,"4":4,"5":5,"6":6,"7":7,"8":8,"9":9,"10":10,
    "primero":1,"primer":1,"la primera":1,"el primero":1,
    "segunda":2,"segundo":2,"la segunda":2,"el segundo":2,
    "tercera":3,"tercero":3,"la tercera":3,"el tercero":3,
    "cuarta":4,"cuarto":4,"la cuarta":4,"el cuarto":4,
    "quinta":5,"quinto":5,"la quinta":5,"el quinto":5,
    "first":1,"the first":1,"second":2,"the second":2,"third":3,"the third":3,
    "fourth":4,"the fourth":4,"fifth":5,"the fifth":5,
}
_RE_ONLY_NUMBER = re.compile(r"^\s*#?\s*(\d{1,2})\s*$")
_RE_UID = re.compile(r"\b[a-f0-9]{16,}\b", re.I)
_RE_IMDB = re.compile(r"\btt\d{6,9}\b", re.I)

def _parse_selection(msg: str, n_items: int) -> Optional[int]:
    s = (msg or "").strip().lower()
    m = _RE_ONLY_NUMBER.match(s)
    if m:
        i = int(m.group(1))
        if 1 <= i <= n_items: return i-1
    if s in _ORD_MAP:
        i = _ORD_MAP[s]
        if 1 <= i <= n_items: return i-1
    return None

def _pick_by_ids(msg: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    m = _RE_IMDB.search(msg or "")
    if m:
        imdb = m.group(0).lower()
        for r in rows:
            if (r.get("imdb_id") or "").lower() == imdb:
                return r
    m = _RE_UID.search(msg or "")
    if m:
        uid = m.group(0).lower()
        for r in rows:
            if (r.get("uid") or "").lower() == uid:
                return r
    return None

# ===================== Endpoint principal =====================
@router.post("/query", response_model=QueryOut)
def query(payload: QueryIn, response: Response):
    sid, ctx = _ensure_session(payload.session_id)
    response.headers["x-session-id"] = sid

    msg = (payload.message or "").strip()
    if not msg:
        return QueryOut(session_id=sid, step="error",
                        text=_i18n("Escribe una consulta por favor.", "Please type a query.", (payload.language or "es")))

    lang = detect_user_lang(msg, hint=(payload.language or None))

    # Intents simples: saludo / identidad
    if RE_GREET.search(msg):
        return QueryOut(session_id=sid, step="answer",
                        text=_i18n(
                            "¡Hola! Soy el asistente virtual de Fabric, potenciado por IA. Puedo ayudarte con sinopsis, disponibilidad y precios por país/plataforma, y popularidad (HITS, local y global).",
                            "Hello! I’m Fabric Data’s virtual assistant, powered by AI. I can help with metadata, availability & prices by platform/country, and popularity (HITS, local & global).",
                            lang))

    if RE_IDENTITY.search(msg):
        return QueryOut(session_id=sid, step="answer",
                        text=_i18n(
                            "Soy el asistente virtual de Fabric, potenciado por IA. Trabajo de forma determinista (SQL-first) sobre Origin Insights y complemento con IA para clasificar, traducir y responder preguntas abiertas.",
                            "I’m Fabric Data’s virtual assistant, powered by AI. I operate deterministically (SQL-first) over Origin Insights and use AI to classify, translate, and answer open-ended questions.",
                            lang))

    # Contexto FE
    if payload.context_uid and not ctx.get("last_uid"):
        ctx["last_uid"] = payload.context_uid

    # Selección directa
    if payload.select_uid or payload.select_imdb_id:
        ctx["last_uid"] = payload.select_uid
        ctx["last_imdb_id"] = payload.select_imdb_id
        ctx["last_candidates"] = []
        _sess_set(sid, ctx)
        return QueryOut(session_id=sid, step="answer",
                        text=_i18n("Seleccionado. Pide sinopsis o disponibilidad (puedes decir el país).",
                                   "Selected. Ask for synopsis or availability (you may include the country).", lang),
                        selected_uid=payload.select_uid or payload.select_imdb_id)

    # ¿Estábamos en desambiguación y el usuario respondió con número/UID/IMDb?
    if ctx.get("last_candidates"):
        rows = ctx["last_candidates"]
        sel_idx = _parse_selection(msg, len(rows))
        chosen: Optional[Dict[str, Any]] = None
        if sel_idx is not None:
            chosen = rows[sel_idx]
        else:
            chosen = _pick_by_ids(msg, rows)

        if chosen:
            ctx.update({
                "last_uid": chosen.get("uid"),
                "last_imdb_id": chosen.get("imdb_id"),
                "last_title": chosen.get("title"),
                "last_year": chosen.get("year"),
                "last_candidates": [],
            })
            _sess_set(sid, ctx)
            return QueryOut(session_id=sid, step="answer",
                            text=_i18n("Seleccionado. Pide sinopsis o disponibilidad (puedes decir el país).",
                                       "Selected. Ask for synopsis or availability (you may include the country).", lang),
                            selected_uid=chosen.get("uid") or chosen.get("imdb_id"))

    # Intents
    ask_synopsis = bool(RE_SYNOPSIS.search(msg))
    ask_avail    = bool(RE_AVAIL.search(msg))
    ask_hits     = bool(RE_HITS.search(msg))

    # 1) SINOPSIS
    if ask_synopsis:
        uid = ctx.get("last_uid"); imdb = ctx.get("last_imdb_id")
        if not (uid or imdb):
            cands = _search_candidates_from_text(msg)
            if not cands:
                return QueryOut(session_id=sid, step="error",
                                text=_i18n("No encontré coincidencias. Añade año/director o usa comillas.",
                                           "No matches found. Try adding year/director or quotes.", lang))
            rows = [c.model_dump() for c in cands]; pick = _safe_autopick(rows)
            if not pick:
                ctx["last_candidates"] = rows; _sess_set(sid, ctx)
                lst = _format_candidates_list([Candidate(**r) for r in rows])
                return QueryOut(session_id=sid, step="disambiguation",
                                text=_disambig_text(lang) + "\n\n" + lst,
                                candidates=[Candidate(**r) for r in rows],
                                next=NextAction(type="select_candidate", method="POST", endpoint="/query"))
            uid, imdb = pick["uid"], pick.get("imdb_id")
            ctx.update({"last_uid": uid, "last_imdb_id": imdb}); _sess_set(sid, ctx)

        meta = m_meta.get_metadata_by_uid(uid) if uid else None
        if (not meta) and imdb:
            meta = m_meta.get_metadata_by_imdb(imdb)
        if not meta:
            return QueryOut(session_id=sid, step="error",
                            text=_i18n("No se encontraron metadatos.", "No metadata found.", lang))
        meta = dict(meta)
        if uid:  meta["uid"] = uid
        if imdb: meta["imdb_id"] = imdb

        txt = _format_selected_metadata(meta, lang)
        return QueryOut(session_id=sid, step="answer", text=txt, selected_uid=uid or imdb)

    # 2) DISPONIBILIDAD
    if ask_avail:
        uid = ctx.get("last_uid"); imdb = ctx.get("last_imdb_id")
        if not (uid or imdb):
            cands = _search_candidates_from_text(msg)
            if not cands:
                return QueryOut(session_id=sid, step="error",
                                text=_i18n("No encontré coincidencias. Especifica el título (p. ej., ‘Conclave 2024’).",
                                           "No matches found. Provide a title (e.g., ‘Conclave 2024’).", lang))
            rows = [c.model_dump() for c in cands]; pick = _safe_autopick(rows)
            if not pick:
                ctx["last_candidates"] = rows; _sess_set(sid, ctx)
                lst = _format_candidates_list([Candidate(**r) for r in rows])
                return QueryOut(session_id=sid, step="disambiguation",
                                text=_disambig_text(lang) + "\n\n" + lst,
                                candidates=[Candidate(**r) for r in rows],
                                next=NextAction(type="select_candidate", method="POST", endpoint="/query"))
            uid, imdb = pick["uid"], pick.get("imdb_id")
            ctx.update({"last_uid": uid, "last_imdb_id": imdb}); _sess_set(sid, ctx)

        try:
            iso2, pretty = m_countries.guess_country(msg)
        except Exception:
            iso2, pretty = None, None

        if not uid and imdb:
            uid = m_meta.resolve_uid_by_imdb(imdb)

        include_prices = bool(re.search(r"\b(precio|prices?)\b", msg, re.I))
        rows = m_avail.fetch_availability_by_uid(uid, iso2=iso2, with_prices=include_prices) if uid else []
        txt = m_avail.render_availability(
            rows, lang=lang, country_pretty=(pretty or (iso2 if (iso2 and len(str(iso2)) == 2) else "")),
            include_details=False, include_prices=include_prices
        )
        if iso2:
            ctx["last_country"] = iso2; _sess_set(sid, ctx)
        return QueryOut(session_id=sid, step="answer", text=txt, selected_uid=uid or imdb)

    # 3) HITS
    if ask_hits:
        try:
            df, dt_ = m_hits.extract_date_range(msg)
            try:
                iso2, pretty = m_countries.guess_country(msg)
            except Exception:
                iso2, pretty = None, None
            df_s, dt_s, used_year = m_hits.ensure_hits_range(df, dt_, iso2)

            # Si es ranking general, ignorar last_uid
            if _is_global_hits_query(msg) or not (ctx.get("last_uid") or ctx.get("last_imdb_id")):
                # Ranking TOP
                asked_topn = None
                mmm = re.search(r"\btop\s*(\d{1,3})\b", msg, re.I)
                if mmm:
                    try: asked_topn = int(mmm.group(1))
                    except: pass
                series_only = bool(re.search(r"\b(serie|series)\b", msg, re.I))
                movie_only  = bool(re.search(r"\b(pel[ií]cula|pelicula|movie|film)\b", msg, re.I))
                content_type = "series" if (series_only and not movie_only) else ("movie" if (movie_only and not series_only) else None)

                items = m_hits.get_top_hits_by_period(country_iso2=iso2, date_from=df_s, date_to=dt_s,
                                                      limit=(asked_topn or 20), content_type=content_type) or []
                if not items:
                    return QueryOut(session_id=sid, step="answer",
                                    text=_i18n("No hay datos de HITS para ese rango/país.",
                                               "No HITS data for that range/country.", lang))
                txt = m_hits.render_top_hits(items, country=(pretty or iso2), lang=lang,
                                             year_used=used_year, series_only=(content_type == "series"), top_n=asked_topn)
                return QueryOut(session_id=sid, step="answer", text=txt)

            # HITS del título seleccionado (suma anual)
            uid = ctx.get("last_uid"); imdb = ctx.get("last_imdb_id")
            hits_sum = m_hits.get_title_hits_sum(uid=uid, imdb_id=imdb, country_iso2=iso2, date_from=df_s, date_to=dt_s)
            meta = m_meta.get_metadata_by_uid(uid) if uid else (m_meta.get_metadata_by_imdb(imdb) if imdb else {})
            meta = meta or {}
            txt = m_hits.render_title_hits_with_context(meta=meta, hits_sum=hits_sum, lang=lang,
                                                        country_pretty=(pretty or iso2), year_used=used_year)
            return QueryOut(session_id=sid, step="answer", text=txt, selected_uid=uid or imdb)

        except Exception:
            log.exception("HITS error")
            return QueryOut(session_id=sid, step="error",
                            text=_i18n("Ocurrió un error al consultar HITS. Intenta nuevamente (puedes indicar un año).",
                                       "Something went wrong with HITS. Try again (you can include a year).", lang))

    # 4) Búsqueda general (desambiguación o autopick)
    cands = _search_candidates_from_text(msg)
    if cands:
        rows = [c.model_dump() for c in cands]; pick = _safe_autopick(rows)
        if pick:
            ctx.update({"last_uid": pick["uid"], "last_imdb_id": pick.get("imdb_id"),
                        "last_title": pick.get("title"), "last_year": pick.get("year"),
                        "last_candidates": []})
            _sess_set(sid, ctx)
            txt = _i18n(
                f"Único resultado fiable: {pick.get('title')} ({pick.get('year')}). Pide sinopsis o disponibilidad (puedes decir el país).",
                f"Single reliable match: {pick.get('title')} ({pick.get('year')}). Ask for synopsis or availability (you may include the country).",
                lang
            )
            return QueryOut(session_id=sid, step="answer", text=txt, selected_uid=pick["uid"] or pick.get("imdb_id"))

        ctx["last_candidates"] = rows; _sess_set(sid, ctx)
        lst = _format_candidates_list([Candidate(**r) for r in rows])
        return QueryOut(session_id=sid, step="disambiguation",
                        text=_disambig_text(lang) + "\n\n" + lst,
                        candidates=[Candidate(**r) for r in rows],
                        next=NextAction(type="select_candidate", method="POST", endpoint="/query"))

    # 5) Fallback LLM (mediador) — opcional
    if os.getenv("ENABLE_FREEFORM_LLM", "0") == "1":
        try:
            from infra.bedrock import call_bedrock_llm1  # lazy
            # Pedimos respuesta breve, en el idioma detectado, y con identidad de marca.
            to_lang = "Spanish" if lang.startswith("es") else "English"
            brand_intro = (
                "Soy el asistente virtual de Fabric, potenciado por IA. "
                "Si tu consulta es sobre metadatos, disponibilidad o HITS, también puedo consultar nuestras bases deterministas."
                if lang.startswith("es") else
                "I’m Fabric Data’s virtual assistant, powered by AI. "
                "If your question is about metadata, availability or HITS, I can also query our deterministic datasets."
            )
            prompt = (
                f"Answer the user's question in {to_lang}. Keep it concise and correct. "
                "If the question requests facts beyond the provided datasets, answer from general knowledge. "
                "Do NOT mention provider names or model names. "
                "Start with a one-line brand-friendly intro, then the answer.\n\n"
                f"Intro line (use this language): {brand_intro}\n\n"
                f"User message:\n{msg}"
            )
            r = call_bedrock_llm1(prompt) or {}
            text = (r.get("completion") or "").strip()
            text = text or ( "No tengo información para eso." if lang.startswith("es") else "I don't have information on that." )
            return QueryOut(session_id=sid, step="answer", text=text)
        except Exception:
            # si falla el LLM, devolvemos mensaje neutro
            return QueryOut(session_id=sid, step="error",
                            text=_i18n("No pude responder eso por ahora.", "I couldn’t answer that right now.", lang))

    # Si llegamos aquí, no hubo matches
    return QueryOut(session_id=sid, step="error",
                    text=_i18n("No encontré coincidencias.", "No matches found.", lang))