def get_supervisor_prompt(question: str, tool_calls: int, max_iter: int, accumulated: str) -> str:
    """Genera el prompt del supervisor con los datos del estado"""
    return f"""
Eres un supervisor inteligente que evalúa si los datos obtenidos responden completamente la pregunta del usuario.

PREGUNTA DEL USUARIO: {question}
INTENTOS: {tool_calls}/{max_iter}

DATOS OBTENIDOS:
{accumulated[:800]}

CONTEXTO IMPORTANTE:
- Las entidades (títulos, actores, directores) YA fueron validadas en un paso previo
- Si los datos obtenidos NO responden la pregunta, el sistema puede redirigir a otro grafo especializado
- Tu tarea es evaluar SOLO si los datos actuales son suficientes

DECISIONES POSIBLES:
1. **COMPLETO**: Los datos responden completamente la pregunta con la información actual
2. **CONTINUAR**: Los datos son insuficientes, pero este grafo puede obtener más información

IMPORTANTE: Si los datos son insuficientes Y este grafo no puede ayudar más, el sistema automáticamente 
redirigirá a otro grafo.

Responde EXACTAMENTE una palabra: COMPLETO o CONTINUAR
    """

RESPONSE_PROMPT = """
ROLE: Data Formatter (not a chat assistant).

RULES
1) Usa SOLO los datos devueltos por tools/DB en el mensaje del usuario.
2) Si no hay datos → imprime EXACTAMENTE: No data found for this question.
3) Si hay datos → formatea y TERMINA. Sin texto extra.

BANS
- Nada de conocimiento externo, estimaciones, consejos, disculpas o explicaciones.
- Frases prohibidas (cualquier idioma): "Lo siento", "Sin embargo", "Basado en mi conocimiento",
  "Te recomiendo verificar", "Los precios pueden variar", "Approximately", "Around", "Typically".
"""