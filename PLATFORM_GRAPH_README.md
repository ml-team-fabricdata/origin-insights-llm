# Platform Graph - Documentación

## 🔄 Flujo del Grafo (CON LOOP)

```
START
  |
  v
[main_supervisor] ←──────────────┐
  |                               |
  +---> ¿Necesita clasificación?  |
  |           |                   |
  |           v                   |
  |     [platform_classifier]     |
  |           |                   |
  |     ┌─────┴─────┐            |
  |     v           v             |
  | [pricing]  [intelligence]     |
  |     └─────┬─────┘            |
  |           |                   |
  +-----------┘ (VUELVE) ─────────┘
  |
  +---> ¿Pregunta respondida?
            |
            v
      [format_response]
            |
            v
           END
```

## 📋 Descripción de Nodos

### 1. **main_supervisor** (Punto Central)
- **Entrada**: Punto de inicio del grafo
- **Primera iteración**: Envía a `platform_classifier`
- **Después de workers**: Evalúa si la pregunta fue respondida
  - ✅ Si COMPLETO → `format_response`
  - ⟳ Si NECESITA_MÁS → `platform_classifier` (loop)

### 2. **platform_classifier**
- Clasifica la pregunta en dos categorías:
  - **PRICING**: Precios, tarifas, costos, suscripciones
  - **INTELLIGENCE**: Disponibilidad, análisis, estadísticas, insights

### 3. **pricing_worker**
- Ejecuta tools relacionadas con precios
- Después de ejecutar → VUELVE a `main_supervisor`

### 4. **intelligence_worker**
- Ejecuta tools de análisis e insights
- Después de ejecutar → VUELVE a `main_supervisor`

### 5. **format_response**
- Formatea la respuesta final con Claude Sonnet 4
- Salida final del grafo

## 🔁 Características del Loop

1. **Máximo de iteraciones**: Configurable (default: 3)
2. **Evaluación inteligente**: El supervisor usa LLM para evaluar si los datos son suficientes
3. **Prevención de loops infinitos**: Límite estricto de iteraciones
4. **Logs detallados**: Cada nodo imprime su estado para debugging

## 🎯 Ejemplos de Clasificación

### PRICING
- "¿Cuánto cuesta Netflix en Argentina?"
- "Compara precios de Disney+ y HBO Max"
- "¿Cuál es el plan más barato de Spotify?"

### INTELLIGENCE
- "¿Cuántas plataformas hay en Argentina?"
- "¿Dónde puedo ver Stranger Things?"
- "Dame estadísticas de plataformas en Brasil"

## 🧪 Testing

### Ejecutar tests:
```bash
python test_platform_graph.py
```

### Visualizar el grafo:
```bash
python visualize_platform_graph.py
```

### Ver diagrama Mermaid:
1. Ejecuta `python visualize_platform_graph.py`
2. Copia el código Mermaid
3. Pégalo en https://mermaid.live

## 📁 Estructura de Archivos

```
src/strands/platform/
├── graph/
│   ├── state.py              # Definición del State
│   ├── parent_supervisor.py  # Supervisor y classifier
│   ├── parent_routers.py     # Routers de tools
│   └── graph.py              # Construcción del grafo
├── worker_helper.py          # Workers dinámicos
└── prompt_platform.py        # Prompts del sistema
```

## ⚙️ Configuración

### Modelos utilizados:
- **Classifier/Supervisor**: `claude-3-5-haiku-20241022-v1:0`
- **Workers**: `claude-3-5-haiku-20241022-v1:0`
- **Formatter**: `claude-sonnet-4-20250514-v1:0`

### Parámetros ajustables:
```python
# En process_question()
max_iterations = 3  # Máximo de loops permitidos
```

## 🔧 Modificaciones Recientes

### ✅ Implementado (2025-10-08)
1. **Flujo con loop**: Workers vuelven al supervisor para evaluación
2. **Renombrado**: availability → pricing, presence → intelligence
3. **Supervisor inteligente**: Evalúa con LLM si continuar o formatear
4. **Límite de iteraciones**: Previene loops infinitos
5. **Logs mejorados**: Debugging más fácil

## 🚀 Uso Programático

```python
from src.strands.platform.graph.graph import process_question

# Procesar una pregunta
result = await process_question(
    question="¿Cuántas plataformas hay en Argentina?",
    max_iterations=3
)

print(result['answer'])
print(f"Task: {result['task']}")
print(f"Iteraciones: {result['tool_calls_count']}")
```

## 📊 Estado del Grafo

El estado se mantiene a través de un `TypedDict` con:
- `question`: Pregunta del usuario
- `task`: "pricing" o "intelligence"
- `tool_calls_count`: Número de iteraciones
- `accumulated_data`: Datos recopilados
- `supervisor_decision`: Decisión del supervisor
- `answer`: Respuesta final
- `status`: Estado final ("success", "insufficient_data", etc.)
