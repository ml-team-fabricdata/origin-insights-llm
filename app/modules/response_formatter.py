# app/modules/response_formatter.py
import re
from typing import Any, Dict, List, Optional

# ---------------------------
# Limpieza básica de texto
# ---------------------------
_TAG_WRAP = re.compile(r"^\s*<(result|answer|output)>\s*([\s\S]*?)\s*</\1>\s*$", re.I)
_TAGS_INLINE = re.compile(r"</?(?:result|answer|output)\s*>", re.I)
_WS = re.compile(r"[ \t]+\n")  # espacios antes de saltos de línea
_MULTI_NL = re.compile(r"\n{3,}")  # más de 2 saltos seguidos

def _normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    s = str(text)
    m = _TAG_WRAP.search(s)
    if m:
        s = m.group(2)
    s = _TAGS_INLINE.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _WS.sub("\n", s)
    s = _MULTI_NL.sub("\n\n", s)
    return s.strip()

# ---------------------------
# Renderizadores simples
# ---------------------------
def _render_list(items: List[str]) -> str:
    if not items:
        return ""
    lines = []
    for it in items:
        it = _normalize_text(it)
        if it:
            lines.append(f"- {it}")
    return "\n".join(lines)

def _render_kv_table(rows: List[Dict[str, Any]], keys: List[str]) -> str:
    """
    Pensado para tablas cortas (p. ej., top hits ya preformateados por el módulo).
    No intenta alinear columnas; devuelve bullets legibles.
    """
    if not rows or not keys:
        return ""
    out = []
    for r in rows:
        parts = []
        for k in keys:
            v = r.get(k)
            if v is None or v == "":
                continue
            parts.append(f"**{k}**: {v}")
        if parts:
            out.append("- " + " · ".join(parts))
    return "\n".join(out)

# ---------------------------
# API pública del módulo
# ---------------------------
def format(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entrada flexible desde el supervisor:
      - Si trae 'output' (str) -> se limpia y devuelve como 'text'.
      - Si trae 'items' (list[str]) -> bullets.
      - Si trae 'rows' (list[dict]) + 'keys' (list[str]) -> tabla rápida.
      - Si trae 'error' -> ok=False y mensaje limpio.
      - Campo 'metadata' se pasa tal cual (por ej. node_used).

    No intenta traducir ni detectar idioma (eso vive en /query).
    """
    meta = result.get("metadata") or {}
    if result.get("error"):
        return {
            "ok": False,
            "text": _normalize_text(result.get("error") or "Unknown error."),
            "metadata": meta,
        }

    # 1) texto plano
    if isinstance(result.get("output"), str):
        return {
            "ok": True,
            "text": _normalize_text(result.get("output")),
            "metadata": meta,
        }

    # 2) lista simple de strings
    if isinstance(result.get("items"), list) and all(isinstance(x, str) for x in result["items"]):
        return {
            "ok": True,
            "text": _render_list(result["items"]),
            "metadata": meta,
        }

    # 3) lista de dicts + llaves para mostrar
    rows = result.get("rows")
    keys = result.get("keys")
    if isinstance(rows, list) and isinstance(keys, list) and rows and keys:
        return {
            "ok": True,
            "text": _render_kv_table(rows, keys),
            "metadata": meta,
        }

    # 4) fallback: si trae 'data' textual
    if isinstance(result.get("data"), str):
        return {
            "ok": True,
            "text": _normalize_text(result["data"]),
            "metadata": meta,
        }

    # 5) último recurso: repr acotado
    return {
        "ok": True,
        "text": _normalize_text(str(result.get("data") or result)),
        "metadata": meta,
    }