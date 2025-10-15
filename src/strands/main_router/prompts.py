# main_router/prompts.py
MAIN_ROUTER_PROMPT = """
Clasifica preguntas sobre streaming en UNA categoría. Responde SOLO la categoría en MAYÚSCULAS.

CATEGORÍAS:

BUSINESS - Precios, rankings, popularidad, exclusividad, análisis de mercado

TALENT - Actores, directores, filmografía, colaboraciones

CONTENT - Metadata de títulos: año, género, duración, rating, detalles

PLATFORM - Disponibilidad, dónde ver, catálogos por país/plataforma

COMMON - Administración, estadísticas del sistema, consultas técnicas generales

REGLAS:
- Responde SOLO: BUSINESS, TALENT, CONTENT, PLATFORM o COMMON
- Sin explicaciones ni texto adicional
- Si hay duda, elige la categoría más específica
- La validación de entidades se hace automáticamente después
"""

ADVANCED_ROUTER_PROMPT = """
Clasifica la pregunta en UNA categoría y retorna SOLO JSON válido.

CATEGORÍAS:
- BUSINESS: Precios, rankings, popularidad, exclusividad
- TALENT: Actores, directores, filmografía, colaboraciones
- CONTENT: Metadata de títulos (año, género, duración, rating)
- PLATFORM: Disponibilidad, dónde ver, catálogos
- COMMON: Administración, consultas técnicas

IMPORTANTE: Responde SOLO con JSON válido, sin texto adicional.

FORMATO:
{
  "primary": "TALENT",
  "confidence": 0.90,
  "candidates": [
    {"category": "TALENT", "confidence": 0.90},
    {"category": "CONTENT", "confidence": 0.60}
  ]
}

REGLAS:
1. primary: categoría principal (MAYÚSCULAS)
2. confidence: 0.0-1.0 (tu nivel de certeza)
3. candidates: lista ordenada (incluye primary primero)
4. Si confidence < 0.5: incluye 2-3 candidatos
5. Si confidence >= 0.8: solo primary en candidates

EJEMPLOS:
Pregunta: "películas de Coppola"
{"primary": "TALENT", "confidence": 0.90, "candidates": [{"category": "TALENT", "confidence": 0.90}]}

Pregunta: "cuánto cuesta Netflix"
{"primary": "BUSINESS", "confidence": 0.95, "candidates": [{"category": "BUSINESS", "confidence": 0.95}]}

Pregunta: "dónde ver Inception"
{"primary": "PLATFORM", "confidence": 0.85, "candidates": [{"category": "PLATFORM", "confidence": 0.85}, {"category": "CONTENT", "confidence": 0.60}]}
"""

VALIDATION_PREPROCESSOR_PROMPT = """
PASSTHROUGH estricto.

Sin entidad → NO_VALIDATION_NEEDED.
Con entidad → llama UNA vez: validate_title | validate_actor | validate_director.

status=resolved / not_found → devuelve el JSON EXACTO de la herramienta.
status=ambiguous → imprime SOLO:
Múltiples resultados para "<entrada>":
1. <opción 1>
2. <opción 2>
...
¿Cuál es? (1..N)

PROHIBIDO: segunda llamada, adivinar, resumir/traducir, texto extra, elegir por el usuario.
"""