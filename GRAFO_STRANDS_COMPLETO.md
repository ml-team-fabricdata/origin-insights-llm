# Grafo Completo del Sistema Strands

## Arquitectura General

```mermaid
graph TB
    User[Usuario] --> MainRouter[Main Router Graph]
    
    MainRouter --> Business[Business Graph]
    MainRouter --> Talent[Talent Graph]
    MainRouter --> Content[Content Graph]
    MainRouter --> Platform[Platform Graph]
    MainRouter --> Common[Common Graph]
    
    Business --> Intelligence[Intelligence Tools]
    Business --> Pricing[Pricing Tools]
    Business --> Rankings[Rankings Tools]
    
    Talent --> Actors[Actors Tools]
    Talent --> Directors[Directors Tools]
    Talent --> Collaborations[Collaborations Tools]
    
    Content --> Metadata[Metadata Tools]
    Content --> Discovery[Discovery Tools]
    
    Platform --> Availability[Availability Tools]
    Platform --> Presence[Presence Tools]
    
    Common --> Validation[Validation Tools]
    Common --> Admin[Admin Tools]
    
    Intelligence --> DB[(Database)]
    Pricing --> DB
    Rankings --> DB
    Actors --> DB
    Directors --> DB
    Collaborations --> DB
    Metadata --> DB
    Discovery --> DB
    Availability --> DB
    Presence --> DB
    Validation --> DB
    Admin --> DB
```

---

## Main Router Graph (11 Nodos)

```mermaid
graph TB
    START([START]) --> AdvancedRouter[advanced_router<br/>Clasificación LLM<br/>Threshold: 0.75]
    
    AdvancedRouter -->|needs_clarification| Clarifier[clarifier<br/>Solicita parámetros faltantes]
    AdvancedRouter -->|needs_validation| ValidationPreprocessor[validation_preprocessor<br/>Valida entidades]
    AdvancedRouter -->|routing_done| DomainGraph[domain_graph<br/>Ejecuta grafo de dominio]
    
    ValidationPreprocessor -->|parallel_execution| ParallelExecutor[parallel_executor<br/>Ejecuta K grafos en paralelo]
    ValidationPreprocessor -->|single_execution| DomainGraph
    ValidationPreprocessor -->|ambiguous| Disambiguation[disambiguation<br/>Resuelve ambigüedad]
    ValidationPreprocessor -->|not_found| NotFoundResponder[not_found_responder<br/>Entidad no encontrada]
    
    ParallelExecutor --> Aggregator[aggregator<br/>Combina resultados]
    
    Aggregator -->|success| DomainGraph
    Aggregator -->|error| ErrorHandler[error_handler<br/>Maneja errores]
    
    DomainGraph -->|success| FormatResponse[format_response<br/>Formatea respuesta final]
    DomainGraph -->|needs_rerouting<br/>hops < 3| AdvancedRouter
    DomainGraph -->|needs_clarification| Clarifier
    DomainGraph -->|error| ErrorHandler
    
    FormatResponse --> ResponderFormatter[responder_formatter<br/>Formato final]
    Clarifier --> ResponderFormatter
    Disambiguation --> ResponderFormatter
    NotFoundResponder --> ResponderFormatter
    ErrorHandler --> ResponderFormatter
    
    ResponderFormatter --> END([END])
    
    style AdvancedRouter fill:#e1f5ff
    style DomainGraph fill:#fff4e1
    style ResponderFormatter fill:#e8f5e9
```

---

## Business Graph (6 Nodos)

```mermaid
graph TB
    START([START]) --> MainSupervisor[main_supervisor<br/>Evalúa completitud]
    
    MainSupervisor -->|NECESITA_CLASIFICACION| BusinessClassifier[business_classifier<br/>Clasifica: intelligence/pricing/rankings]
    MainSupervisor -->|COMPLETO| FormatResponse[format_response<br/>Formatea respuesta]
    MainSupervisor -->|VOLVER_MAIN_ROUTER| RETURN([RETURN TO MAIN])
    
    BusinessClassifier -->|intelligence| IntelligenceNode[intelligence_node<br/>Router → Agent → Tools]
    BusinessClassifier -->|pricing| PricingNode[pricing_node<br/>Router → Agent → Tools]
    BusinessClassifier -->|rankings| RankingsNode[rankings_node<br/>Router → Agent → Tools]
    
    IntelligenceNode --> MainSupervisor
    PricingNode --> MainSupervisor
    RankingsNode --> MainSupervisor
    
    FormatResponse --> END([END])
    
    style BusinessClassifier fill:#e1f5ff
    style IntelligenceNode fill:#fff4e1
    style PricingNode fill:#fff4e1
    style RankingsNode fill:#fff4e1
    style FormatResponse fill:#e8f5e9
```

### Intelligence Node - Tools

```mermaid
graph LR
    IntelligenceNode[Intelligence Node] --> Router[Router LLM]
    
    Router --> Tool1[get_platform_exclusivity_by_country]
    Router --> Tool2[catalog_similarity_for_platform]
    Router --> Tool3[titles_in_A_not_in_B_sql]
    
    Tool1 --> Cache{Cache?}
    Tool2 --> Cache
    Tool3 --> Cache
    
    Cache -->|Hit| Return[Return cached]
    Cache -->|Miss| DB[(Database Query<br/>50-100s)]
    
    DB --> SaveCache[Save to cache<br/>TTL: 60min]
    SaveCache --> Return
    
    style Cache fill:#ffe1e1
    style DB fill:#e1e1ff
```

### Pricing Node - Tools

```mermaid
graph LR
    PricingNode[Pricing Node] --> Router[Router LLM]
    
    Router --> Tool1[tool_prices_latest]
    Router --> Tool2[tool_prices_history]
    Router --> Tool3[tool_prices_changes_last_n_days]
    Router --> Tool4[tool_prices_stats]
    Router --> Tool5[tool_prices_quality_check]
    
    Tool1 --> DB[(Database)]
    Tool2 --> DB
    Tool3 --> DB
    Tool4 --> DB
    Tool5 --> DB
    
    style DB fill:#e1e1ff
```

### Rankings Node - Tools

```mermaid
graph LR
    RankingsNode[Rankings Node] --> Router[Router LLM]
    
    Router --> Tool1[get_genre_momentum]
    Router --> Tool2[get_top_by_uid]
    Router --> Tool3[get_top_generic]
    Router --> Tool4[get_top_presence]
    Router --> Tool5[get_top_global]
    
    Tool1 --> Cache{Cache?}
    Tool2 --> Cache
    Tool3 --> Cache
    Tool4 --> Cache
    Tool5 --> Cache
    
    Cache -->|Hit| Return[Return cached]
    Cache -->|Miss| DB[(Database)]
    
    DB --> SaveCache[Save to cache<br/>TTL: 30min]
    SaveCache --> Return
    
    style Cache fill:#ffe1e1
    style DB fill:#e1e1ff
```

---

## Talent Graph (6 Nodos)

```mermaid
graph TB
    START([START]) --> MainSupervisor[main_supervisor<br/>Evalúa completitud]
    
    MainSupervisor -->|NECESITA_CLASIFICACION| TalentClassifier[talent_classifier<br/>Clasifica: actors/directors/collaborations]
    MainSupervisor -->|COMPLETO| FormatResponse[format_response]
    MainSupervisor -->|VOLVER_MAIN_ROUTER| RETURN([RETURN TO MAIN])
    
    TalentClassifier -->|actors| ActorsNode[actors_node<br/>Con validated_entities]
    TalentClassifier -->|directors| DirectorsNode[directors_node<br/>Con validated_entities]
    TalentClassifier -->|collaborations| CollaborationsNode[collaborations_node<br/>Con validated_entities]
    
    ActorsNode --> MainSupervisor
    DirectorsNode --> MainSupervisor
    CollaborationsNode --> MainSupervisor
    
    FormatResponse --> END([END])
    
    style TalentClassifier fill:#e1f5ff
    style ActorsNode fill:#fff4e1
    style DirectorsNode fill:#fff4e1
    style CollaborationsNode fill:#fff4e1
```

---

## Content Graph (5 Nodos)

```mermaid
graph TB
    START([START]) --> MainSupervisor[main_supervisor<br/>Evalúa completitud]
    
    MainSupervisor -->|NECESITA_CLASIFICACION| ContentClassifier[content_classifier<br/>Clasifica: metadata/discovery]
    MainSupervisor -->|COMPLETO| FormatResponse[format_response]
    MainSupervisor -->|VOLVER_MAIN_ROUTER| RETURN([RETURN TO MAIN])
    
    ContentClassifier -->|metadata| MetadataNode[metadata_node<br/>Con validated_entities]
    ContentClassifier -->|discovery| DiscoveryNode[discovery_node<br/>Con validated_entities]
    
    MetadataNode --> MainSupervisor
    DiscoveryNode --> MainSupervisor
    
    FormatResponse --> END([END])
    
    style ContentClassifier fill:#e1f5ff
    style MetadataNode fill:#fff4e1
    style DiscoveryNode fill:#fff4e1
```

---

## Platform Graph (5 Nodos)

```mermaid
graph TB
    START([START]) --> MainSupervisor[main_supervisor<br/>Evalúa completitud]
    
    MainSupervisor -->|NECESITA_CLASIFICACION| PlatformClassifier[platform_classifier<br/>Clasifica: availability/presence]
    MainSupervisor -->|COMPLETO| FormatResponse[format_response]
    MainSupervisor -->|VOLVER_MAIN_ROUTER| RETURN([RETURN TO MAIN])
    
    PlatformClassifier -->|availability| AvailabilityNode[availability_node]
    PlatformClassifier -->|presence| PresenceNode[presence_node]
    
    AvailabilityNode --> MainSupervisor
    PresenceNode --> MainSupervisor
    
    FormatResponse --> END([END])
    
    style PlatformClassifier fill:#e1f5ff
    style AvailabilityNode fill:#fff4e1
    style PresenceNode fill:#fff4e1
```

---

## Common Graph (5 Nodos)

```mermaid
graph TB
    START([START]) --> MainSupervisor[main_supervisor<br/>Evalúa completitud]
    
    MainSupervisor -->|NECESITA_CLASIFICACION| CommonClassifier[common_classifier<br/>Clasifica: validation/admin]
    MainSupervisor -->|COMPLETO| FormatResponse[format_response]
    MainSupervisor -->|VOLVER_MAIN_ROUTER| RETURN([RETURN TO MAIN])
    
    CommonClassifier -->|validation| ValidationNode[validation_node]
    CommonClassifier -->|admin| AdminNode[admin_node]
    
    ValidationNode --> MainSupervisor
    AdminNode --> MainSupervisor
    
    FormatResponse --> END([END])
    
    style CommonClassifier fill:#e1f5ff
    style ValidationNode fill:#fff4e1
    style AdminNode fill:#fff4e1
```

---

## Flujo de Ejecución Completo

```mermaid
sequenceDiagram
    participant User
    participant MainRouter
    participant ValidationPreprocessor
    participant DomainGraph
    participant Supervisor
    participant Classifier
    participant Node
    participant Router
    participant Agent
    participant Tool
    participant Cache
    participant DB
    
    User->>MainRouter: Question
    MainRouter->>MainRouter: advanced_router (classify)
    
    alt Needs Validation (talent/content)
        MainRouter->>ValidationPreprocessor: Validate entities
        ValidationPreprocessor->>DB: validate_actor/director/title
        DB-->>ValidationPreprocessor: entity_id
        ValidationPreprocessor-->>MainRouter: validated_entities
    end
    
    MainRouter->>DomainGraph: Execute domain graph
    DomainGraph->>Supervisor: Evaluate state
    
    alt Needs Classification
        Supervisor->>Classifier: Classify task
        Classifier-->>Supervisor: task type
        Supervisor->>Node: Execute node
        
        Node->>Router: Select tool
        Router-->>Node: tool_name
        
        Node->>Agent: Execute with tool
        Agent->>Tool: Call tool
        
        Tool->>Cache: Check cache
        
        alt Cache Hit
            Cache-->>Tool: Cached result
        else Cache Miss
            Tool->>DB: Query database
            DB-->>Tool: Result (50-100s)
            Tool->>Cache: Save to cache
        end
        
        Tool-->>Agent: Result
        Agent-->>Node: Formatted result
        Node-->>Supervisor: accumulated_data
    end
    
    Supervisor->>Supervisor: Evaluate completeness
    
    alt Complete
        Supervisor->>DomainGraph: COMPLETO
        DomainGraph->>DomainGraph: format_response
        DomainGraph-->>MainRouter: Final answer
    else Needs More
        Supervisor->>Classifier: Continue
        Note over Supervisor,Classifier: Loop (max 3 iterations)
    else Not My Scope
        Supervisor->>DomainGraph: VOLVER_MAIN_ROUTER
        DomainGraph-->>MainRouter: Re-route
        Note over MainRouter: Re-routing (max 3 hops)
    end
    
    MainRouter->>MainRouter: responder_formatter
    MainRouter-->>User: Final Response
```

---

## Decisiones del Supervisor

```mermaid
graph TD
    Start([Supervisor Decision]) --> CheckToolCalls{tool_calls == 0?}
    
    CheckToolCalls -->|Yes| CLASIFICAR[NECESITA_CLASIFICACION]
    CheckToolCalls -->|No| CheckLength{len < 50?}
    
    CheckLength -->|Yes| REROUTEAR[VOLVER_MAIN_ROUTER]
    CheckLength -->|No| CheckGeneric{Generic phrases?}
    
    CheckGeneric -->|Yes| REROUTEAR
    CheckGeneric -->|No| LLMEvaluate[LLM Evaluate]
    
    LLMEvaluate -->|Complete data| COMPLETO[COMPLETO]
    LLMEvaluate -->|Needs more| CONTINUAR[NECESITA_CLASIFICACION]
    LLMEvaluate -->|Wrong domain| REROUTEAR
    
    style CLASIFICAR fill:#e1f5ff
    style COMPLETO fill:#e8f5e9
    style REROUTEAR fill:#ffe1e1
    style CONTINUAR fill:#fff4e1
```

---

## Estrategia de Cache

```mermaid
graph TB
    Request[Request] --> CheckCache{Cache exists?}
    
    CheckCache -->|Yes| CheckTTL{TTL valid?}
    CheckCache -->|No| ExecuteQuery[Execute Query]
    
    CheckTTL -->|Yes| ReturnCache[Return cached<br/>~0.1s]
    CheckTTL -->|No| ExecuteQuery
    
    ExecuteQuery --> DB[(Database<br/>50-100s)]
    DB --> SaveCache[Save to cache]
    SaveCache --> Return[Return result]
    
    subgraph Cache Strategy
        Intelligence[Intelligence<br/>TTL: 60min<br/>Size: 500]
        Rankings[Rankings<br/>TTL: 30min<br/>Size: 500]
        Pricing[Pricing<br/>TTL: 15min<br/>Size: 500]
    end
    
    style ReturnCache fill:#e8f5e9
    style DB fill:#e1e1ff
```

---

## Re-routing Logic

```mermaid
graph TD
    Start([Domain Graph Result]) --> CheckStatus{Status?}
    
    CheckStatus -->|success| SchemaChecker[schema_checker]
    CheckStatus -->|not_my_scope| CheckHops{hops < 3?}
    CheckStatus -->|error| ErrorHandler[error_handler]
    
    CheckHops -->|Yes| AddVisited[Add to visited_graphs]
    CheckHops -->|No| MaxHops[Max hops reached]
    
    AddVisited --> AdvancedRouter[advanced_router<br/>Re-classify]
    MaxHops --> ErrorHandler
    
    SchemaChecker -->|valid| FormatResponse[format_response]
    SchemaChecker -->|invalid| ErrorHandler
    
    FormatResponse --> End([END])
    ErrorHandler --> End
    
    style SchemaChecker fill:#e1f5ff
    style FormatResponse fill:#e8f5e9
    style ErrorHandler fill:#ffe1e1
```

---

## Métricas de Performance

### Tiempos de Ejecución

| Componente | Cache Hit | Cache Miss | Promedio |
|------------|-----------|------------|----------|
| **Main Router** | - | - | 2-5s |
| **Validation** | - | - | 1-3s |
| **Domain Graph** | - | - | 1-2s |
| **Tool Execution** | <0.1s | 50-100s | 30-60s |
| **Format Response** | - | - | 1-2s |
| **TOTAL** | 10-15s | 60-110s | 40-70s |

### Hit Rate de Cache

- **Intelligence**: 40-60% hit rate
- **Rankings**: 30-50% hit rate
- **Pricing**: 20-40% hit rate

### Límites del Sistema

- **Max Hops**: 3 re-routings entre grafos
- **Max Iterations**: 3 iteraciones por domain graph
- **Max Parallel**: 3 grafos en paralelo
- **Confidence Threshold**: 0.75 para single execution

---

## Configuración de Dominios

### Confidence Thresholds

```python
DOMAIN_CONFIDENCE_THRESHOLDS = {
    "talent": 0.75,      # Alta precisión requerida
    "platform": 0.70,    # Precisión media-alta
    "business": 0.70,    # Precisión media-alta
    "content": 0.68,     # Precisión media
    "common": 0.50       # Fallback domain
}
```

### Grafos que Requieren Validación

```python
GRAPHS_REQUIRING_VALIDATION = ["talent", "content"]
```

### Grafos Seguros para Paralelización

```python
SAFE_PARALLEL_GRAPHS = {"talent", "content", "common"}
UNSAFE_PARALLEL_GRAPHS = {"business", "platform"}
```

---

## Estado del Sistema (State)

### MainRouterState

```typescript
{
    question: str
    answer: str
    selected_graph: "business" | "talent" | "content" | "platform" | "common"
    routing_confidence: float
    routing_candidates: List[(graph, score)]
    visited_graphs: List[str]
    validated_entities: Dict[str, Any]
    needs_validation: bool
    needs_clarification: bool
    needs_rerouting: bool
    parallel_execution: bool
    parallel_k: int
    rerouting_count: int
    max_hops: int
    tool_execution_times: Dict[str, float]
    telemetry_logger: TelemetryLogger
}
```

### Domain State (Business/Talent/Content/Platform/Common)

```typescript
{
    question: str
    answer: str
    task: str  // Tipo específico del dominio
    tool_calls_count: int
    max_iterations: int
    accumulated_data: str
    supervisor_decision: str
    needs_more: bool
    classification_done: bool
    status: "success" | "insufficient_data" | "format_error" | "max_iterations"
    last_node: str
    should_continue: bool
    tool_execution_times: Dict[str, float]
    validated_entities: Dict[str, Any]  // Solo talent/content
}
```

---

## Resumen de Componentes

### Total de Nodos

- **Main Router**: 11 nodos
- **Business**: 6 nodos (3 workers)
- **Talent**: 6 nodos (3 workers)
- **Content**: 5 nodos (2 workers)
- **Platform**: 5 nodos (2 workers)
- **Common**: 5 nodos (2 workers)
- **TOTAL**: 38 nodos

### Total de Tools

- **Intelligence**: 3 tools
- **Pricing**: 5 tools
- **Rankings**: 5 tools
- **Actors**: ~5 tools
- **Directors**: ~5 tools
- **Collaborations**: ~3 tools
- **Metadata**: ~5 tools
- **Discovery**: ~5 tools
- **Availability**: ~5 tools
- **Presence**: ~5 tools
- **Validation**: ~3 tools
- **Admin**: ~5 tools
- **TOTAL**: ~54 tools

### Factories Utilizados

1. **BaseExecutorNode**: Clase base para ejecutores de nodos
2. **create_router()**: Factory para routers LLM
3. **create_simple_classifier()**: Factory para classifiers
4. **QueryCache**: Sistema de caché con TTL

---

## Conclusión

El sistema Strands es una arquitectura de grafos multinivel que:

1. **Clasifica** preguntas en el Main Router
2. **Valida** entidades cuando es necesario (talent/content)
3. **Ejecuta** el grafo de dominio apropiado
4. **Supervisa** la completitud de la respuesta
5. **Re-enruta** si el dominio no es el correcto
6. **Cachea** resultados para optimizar performance
7. **Formatea** la respuesta final

Con soporte para:
- ✅ Ejecución paralela de múltiples grafos
- ✅ Re-routing inteligente entre dominios
- ✅ Validación de entidades
- ✅ Cache con TTL por dominio
- ✅ Tracking de tiempos de ejecución
- ✅ Telemetría completa
