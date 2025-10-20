# 📋 Plan de Migración Detallado - Clean Architecture

## ⚠️ IMPORTANTE
- NO borrar archivos viejos hasta completar testing
- Mantener ambas estructuras en paralelo durante migración
- Actualizar imports gradualmente

---

## 🎯 Fase 1: Prompts (2-3 horas) ✅ SAFE

### Archivos a migrar:
1. `business/nodes/prompt_business.py` → `prompts/business/`
   - INTELLIGENCE_PROMPT → `intelligence.py`
   - PRICING_PROMPT → `pricing.py`
   - RANKINGS_PROMPT → `rankings.py`

2. `src/prompt.py` → `prompts/shared/`
   - get_supervisor_prompt() → `supervisor.py`
   - RESPONSE_PROMPT → `formatter.py`

### Comandos:
```bash
# Copiar contenido de prompt_business.py
# Dividir en 3 archivos separados
# Cada prompt en su propio archivo
```

### Testing:
```python
# Verificar imports
from prompts.business.intelligence import INTELLIGENCE_PROMPT
from prompts.shared.supervisor import get_supervisor_prompt
```

---

## 🎯 Fase 2: Cache (1-2 horas) ✅ SAFE

### Archivos a migrar:
1. `utils/query_cache.py` → `infrastructure/cache/query_cache.py`

### Cambios:
- Implementar interface `CacheRepository`
- Mantener misma funcionalidad
- Actualizar imports

### Testing:
```python
from infrastructure.cache.query_cache import intelligence_cache
assert intelligence_cache.get_stats()['size'] == 0
```

---

## 🎯 Fase 3: Validators (2-3 horas) ⚠️ MEDIUM RISK

### Archivos a migrar:
1. `utils/validators_shared.py` → Split into:
   - `infrastructure/validators/country_validator.py`
   - `infrastructure/validators/platform_validator.py`
   - `infrastructure/validators/date_validator.py`
   - `infrastructure/validators/shared_validators.py`

### Testing:
- Run all existing tests
- Verify all imports work

---

## 🎯 Fase 4: Queries (3-4 horas) ⚠️ MEDIUM RISK

### Archivos a migrar:
1. `business/business_queries/intelligence_queries.py` → Split into:
   - `infrastructure/database/queries/intelligence/exclusivity_queries.py`
   - `infrastructure/database/queries/intelligence/similarity_queries.py`
   - `infrastructure/database/queries/intelligence/comparison_queries.py`

### Por cada query:
- Extraer a archivo separado
- Documentar parámetros
- Agregar tests

---

## 🎯 Fase 5: Use Cases (4-5 horas) 🔴 HIGH RISK

### Archivos a migrar:
1. `business/business_modules/intelligence.py` → Split into:
   - `core/use_cases/intelligence/get_exclusivity.py`
   - `core/use_cases/intelligence/catalog_similarity.py`
   - `core/use_cases/intelligence/compare_regions.py`

### Cambios importantes:
- Inyectar dependencias (repositories)
- Separar business logic de infrastructure
- Mantener @tool decorators

---

## 🎯 Fase 6: Graphs (5-6 horas) 🔴 HIGH RISK

### Última fase - cuando todo lo demás funcione

### Archivos a migrar:
1. `business/graph_core/` → `graphs/business/`
2. `business/nodes/` → `graphs/business/nodes/`

---

## 📊 Checklist de Migración

### Por cada archivo migrado:
- [ ] Archivo creado en nueva ubicación
- [ ] Contenido copiado y adaptado
- [ ] Imports actualizados
- [ ] Tests ejecutados
- [ ] Documentación actualizada
- [ ] Old imports marked as deprecated
- [ ] Performance verificada

### Antes de borrar archivos viejos:
- [ ] Todas las tests pasan
- [ ] Performance igual o mejor
- [ ] Sin errores en producción por 1 semana
- [ ] Backup creado
- [ ] Rollback plan documentado

---

## 🔄 Rollback Plan

Si algo falla en cualquier fase:

```python
# Revertir imports a estructura vieja
# Los archivos viejos siguen ahí durante migración
```

---

## 📈 Métricas de Éxito

- [ ] 0 breaking changes
- [ ] Performance igual o mejor
- [ ] Cobertura de tests ≥ 90%
- [ ] Todos los imports funcionan
- [ ] Documentación actualizada
