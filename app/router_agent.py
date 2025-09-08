# app/router_agent.py
from __future__ import annotations
from typing import Optional, Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

from infra.config import SETTINGS
from app.llm.postprocess import rewrite_for_user_language
from app.agent import tools as T
from app.agent.sqlgen import try_sql_answer

router = APIRouter(prefix="/v1/agent", tags=["agent"])

# ---------- Modelos ----------
class AgentIn(BaseModel):
    text: str
    lang: Optional[str] = None
    uid: Optional[str] = None
    country: Optional[str] = None

class AgentOut(BaseModel):
    kind: str
    payload: Dict[str, Any]

# ---------- Helpers ----------
def _lang_hint(q: str, hint: Optional[str]) -> str:
    l = (hint or "").lower()
    if l in ("es","en"):
        return l
    ql = (q or "").lower()
    if "¿" in q or "¡" in q or any(w in ql for w in ["qué","cual","popularidad","disponibilidad","sinopsis"]):
        return "es"
    return "en"

# ---------- Endpoint principal ----------
@router.post("/ask", response_model=AgentOut)
def agent_ask(payload: AgentIn) -> AgentOut:
    q = (payload.text or "").strip()
    lang = _lang_hint(q, payload.lang)

    # 1) Si trae UID → intentá popularidad del título con contexto
    if payload.uid:
        try:
            pop = T.tool_hits_title_with_context(uid=payload.uid, user_text=q)
            final = rewrite_for_user_language(pop["text"], user_query=q, target_lang_hint=lang)
            return AgentOut(kind="deterministic.popularity", payload={"text": final, "meta": pop.get("meta", {})})
        except Exception:
            pass

    # 2) ¿Pide top?
    import re
    if re.search(r"\b(top\s*\d{0,3}|ranking|más\s+populares|mas\s+populares|populares)\b", q, re.I):
        txt = T.tool_hits_top(q)
        if txt:
            final = rewrite_for_user_language(txt, user_query=q, target_lang_hint=lang)
            return AgentOut(kind="deterministic.top", payload={"text": final})
        # si no hay datos, seguimos a fallback

    # 3) ¿Menciona popularidad/HITS de un título pero sin UID? Intentar búsqueda + meta + hits
    if re.search(r"\b(popularidad|hits?)\b", q, re.I):
        # sacar candidatos
        term = T.tool_titles_search(q)
        if term:
            # si autopick “visual”: tomamos primero; el UI/FE puede confirmar luego
            cand = term[0]
            uid = cand.get("uid")
            if uid:
                pop = T.tool_hits_title_with_context(uid=uid, user_text=q)
                final = rewrite_for_user_language(pop["text"], user_query=q, target_lang_hint=lang)
                return AgentOut(kind="deterministic.popularity", payload={"text": final, "meta": {"uid": uid}})

    # 4) SQL gen seguro (experimental)
    sql_attempt = try_sql_answer(q)
    if sql_attempt:
        # formateo breve: primeras filas tabulares en texto simple
        rows = sql_attempt["rows"]
        if rows:
            # render simple en ES (se reescribe luego)
            cols = list(rows[0].keys())
            lines = ["Resultado (primeras filas):", ", ".join(cols)]
            for r in rows[:10]:
                lines.append(", ".join(str(r.get(c)) if r.get(c) is not None else "" for c in cols))
            body = "\n".join(lines)
        else:
            body = "La consulta no devolvió filas."
        final = rewrite_for_user_language(body, user_query=q, target_lang_hint=lang)
        return AgentOut(kind="sqlgen", payload={"text": final, "sql": sql_attempt["sql"]})

    # 5) Fallback: LLM libre (si está habilitado)
    if SETTINGS.enable_freeform_llm:
        try:
            from app.router_llm import ask_llm, LLMQueryIn  # type: ignore
            r = ask_llm(LLMQueryIn(text=q, lang=lang))
            ans = (r.payload.get("answer") or r.payload.get("message")) if isinstance(r.payload, dict) else None
            if ans:
                # ya viene con tono; igual lo pasamos por rewrite por consistencia
                final = rewrite_for_user_language(ans, user_query=q, target_lang_hint=lang)
                return AgentOut(kind="llm.freeform", payload={"text": final})
        except Exception:
            pass

    # 6) Mensaje guía
    guide = (
        "Puedo ayudarte con sinopsis, disponibilidad por país/plataforma y popularidad (HITS). "
        "Por ejemplo: “popularidad de Conclave (2025)”, “top 10 películas global 2025”, "
        "o “dónde ver The Office en Argentina”."
        if lang == "es"
        else
        "I can help with synopsis, availability by country/platform, and popularity (HITS). "
        "For example: “popularity of Conclave (2025)”, “top 10 movies global 2025”, "
        "or “where to watch The Office in Argentina”."
    )
    final = rewrite_for_user_language(guide, user_query=q, target_lang_hint=lang)
    return AgentOut(kind="help", payload={"text": final})