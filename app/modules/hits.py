# app/hits.py
"""
Shim de compatibilidad: reexporta las funciones canónicas desde app/modules/hits.py
para evitar duplicar lógica y prevenir divergencias.
Si el código legacy importa `app.hits`, seguirá funcionando.
"""

from typing import Optional, Dict, Any, List

# Reexport canónico
from app.modules.hits import (
    get_title_hits_sum,
    get_top_hits_by_period,
    render_title_hits_with_context,
)

__all__ = [
    "get_title_hits_sum",
    "get_top_hits_by_period",
    "render_title_hits_with_context",
]