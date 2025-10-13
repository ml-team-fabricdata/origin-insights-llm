# 🎯 Main Router - Super Supervisor

El **Main Router** es el punto de entrada principal del sistema. Decide automáticamente a qué grafo especializado debe dirigir cada pregunta.

## 🏗️ Arquitectura

```
Usuario → Main Router → [Business|Talent|Content|Platform|Common] Graph → Respuesta
```

## 📊 Grafos Disponibles

| Grafo | Descripción | Ejemplos |
|-------|-------------|----------|
| **Business** | Precios, rankings, exclusividad, análisis de mercado | "¿Cuánto cuesta Netflix?" |
| **Talent** | Actores, directores, filmografías, colaboraciones | "¿Qué ha dirigido Nolan?" |
| **Content** | Metadata de títulos, ratings, géneros, años | "¿De qué año es Inception?" |
| **Platform** | Disponibilidad, presencia, catálogos por país | "¿Dónde puedo ver X?" |
| **Common** | Validación de datos, administración del sistema | "¿Existe este actor?" |

## 🚀 Uso

### Básico

```python
from src.strands.main_router.graph import process_question_main

result = await process_question_main("¿Cuánto cuesta Netflix en Argentina?")

print(result['answer'])
# → "Netflix en Argentina cuesta aproximadamente..."

print(result['selected_graph'])
# → "business"
```

### Con Streaming

```python
from src.strands.main_router.graph import process_question_main_streaming

async for event in process_question_main_streaming("¿Dónde ver Inception?"):
    node_name = list(event.keys())[0]
    print(f"Procesando: {node_name}")
```

### Configurar Max Iteraciones

```python
result = await process_question_main(
    "¿Qué películas ha hecho DiCaprio?",
    max_iterations=5  # Más iteraciones = más datos
)
```

## 🧪 Testing

```bash
# Test del router
python test_main_router.py

# Test de todos los grafos
python test_all_graphs.py
```

## 🔧 Componentes

### 1. `router.py` - Clasificador Principal
- Usa LLM para clasificar la pregunta
- Retorna: `business`, `talent`, `content`, `platform` o `common`
- Tiene fallbacks basados en keywords

### 2. `graph.py` - Orquestador
- Construye el grafo principal con LangGraph
- Conecta el router con los 5 sub-grafos
- Maneja el flujo completo de inicio a fin

### 3. `state.py` - Estado
```python
class MainRouterState(TypedDict):
    question: str                    # Pregunta del usuario
    answer: str                      # Respuesta final
    selected_graph: str              # Grafo seleccionado
    routing_done: bool               # Flag de routing completado
    error: Optional[str]             # Errores si los hay
```

### 4. `prompts.py` - Prompts de Clasificación
- Prompt detallado con ejemplos para cada categoría
- Instrucciones claras para el LLM clasificador

## 📈 Flujo Detallado

```
1. Usuario envía pregunta
   ↓
2. Main Router recibe pregunta
   ↓
3. LLM clasifica en una de 5 categorías
   ↓
4. Router condicional dirige al grafo correcto
   ↓
5. Sub-grafo procesa la pregunta:
   - Main Supervisor del sub-grafo
   - Classifier específico (pricing/actors/metadata/etc)
   - Worker nodes ejecutan tools
   - Supervisor evalúa si hay datos suficientes
   - Format response genera respuesta
   ↓
6. Respuesta retorna al Main Router
   ↓
7. Main Router retorna al usuario
```

## 🎯 Criterios de Clasificación

El router usa estos criterios para decidir:

### BUSINESS
- **Keywords:** precio, cuesta, cost, ranking, popular, exclusiv, mercado
- **Patrones:** "¿Cuánto...?", "¿Qué es lo más...?", "¿Qué tiene X que no tiene Y?"

### TALENT
- **Keywords:** actor, actriz, director, dirigid, filmograf, colabor
- **Patrones:** "¿Qué ha hecho...?", "¿Quién dirigió...?", "¿En qué trabajaron...?"

### CONTENT
- **Keywords:** año, duraci, rating, género, imdb, metadata
- **Patrones:** "¿De qué año...?", "¿Cuánto dura...?", "¿Qué rating...?"

### PLATFORM
- **Keywords:** donde, ver, disponible, plataforma, netflix, disney, hbo
- **Patrones:** "¿Dónde puedo ver...?", "¿Está en...?", "¿Qué tiene Netflix?"

### COMMON
- **Keywords:** existe, válido, validar, admin, sistema
- **Patrones:** "¿Existe...?", "¿Es válido...?", "Estadísticas del sistema"

## ⚠️ Fallbacks

Si el LLM no retorna una categoría válida, el router:

1. Busca keywords en la respuesta del LLM
2. Si no encuentra, analiza keywords en la pregunta original
3. Si todo falla, usa `common` como fallback

## 🔍 Debugging

### Ver qué grafo se seleccionó

```python
result = await process_question_main("Tu pregunta")
print(f"Grafo usado: {result['selected_graph']}")
```

### Ver el proceso completo

```python
# Activa los prints en router.py (ya están incluidos)
result = await process_question_main("Tu pregunta")

# Output:
# 🎯 MAIN GRAPH ROUTER
# 📝 Pregunta: Tu pregunta
# [ROUTER] Decisión raw: BUSINESS
# [ROUTER] ✅ Grafo seleccionado: business
# 🏢 Ejecutando BUSINESS GRAPH...
```

## 📝 Ejemplos Completos

### Ejemplo 1: Pregunta de Precios

```python
result = await process_question_main("¿Cuánto cuesta Disney+ en México?")

# Router selecciona: business
# Business classifier selecciona: pricing
# Pricing node ejecuta: tool_prices_latest
# Respuesta: "Disney+ en México cuesta..."
```

### Ejemplo 2: Pregunta de Disponibilidad

```python
result = await process_question_main("¿Dónde puedo ver Breaking Bad?")

# Router selecciona: platform
# Platform classifier selecciona: availability
# Availability node ejecuta: check_title_availability
# Respuesta: "Breaking Bad está disponible en Netflix, Amazon Prime..."
```

### Ejemplo 3: Pregunta de Talento

```python
result = await process_question_main("¿Qué películas ha dirigido Tarantino?")

# Router selecciona: talent
# Talent classifier selecciona: directors
# Directors node ejecuta: get_director_filmography
# Respuesta: "Quentin Tarantino ha dirigido: Pulp Fiction (1994)..."
```

## 🎨 Personalización

### Agregar nuevo grafo

1. Crear el grafo en `src/strands/nuevo_grafo/`
2. Importar en `graph.py`:
```python
from src.strands.nuevo_grafo.graph_core.graph import process_question as nuevo_process
```

3. Agregar nodo:
```python
async def nuevo_graph_node(state: MainRouterState) -> MainRouterState:
    result = await nuevo_process(state['question'])
    return {**state, "answer": result.get('answer')}
```

4. Actualizar router en `router.py` y `prompts.py`

### Modificar criterios de clasificación

Edita `prompts.py` → `MAIN_ROUTER_PROMPT` para ajustar las descripciones y ejemplos.

## 📊 Métricas

El router mantiene:
- `selected_graph`: Qué grafo fue seleccionado
- `routing_done`: Si la clasificación ya se completó
- `error`: Cualquier error durante el proceso

## ✅ Ventajas del Main Router

1. **Simplicidad:** Una sola función para todas las preguntas
2. **Escalabilidad:** Fácil agregar nuevos grafos
3. **Mantenibilidad:** Lógica de routing centralizada
4. **Flexibilidad:** Cada grafo es independiente
5. **Observabilidad:** Logs claros del proceso de decisión

---

**Creado:** 2025-01-09  
**Versión:** 1.0.0
