# Migration Mapping

## Old Structure → New Structure

### Prompts
```
OLD: business/nodes/prompt_business.py
NEW: prompts/business/intelligence.py
     prompts/business/pricing.py
     prompts/business/rankings.py

OLD: src/prompt.py (supervisor prompts)
NEW: prompts/shared/supervisor.py
     prompts/shared/formatter.py
```

### Cache
```
OLD: utils/query_cache.py
NEW: infrastructure/cache/query_cache.py
```

### Validators
```
OLD: utils/validators.py
     utils/validators_shared.py
NEW: infrastructure/validators/country_validator.py
     infrastructure/validators/platform_validator.py
     infrastructure/validators/shared_validators.py
```

### Queries
```
OLD: business/business_queries/intelligence_queries.py
NEW: infrastructure/database/queries/intelligence/exclusivity_queries.py
     infrastructure/database/queries/intelligence/similarity_queries.py
     infrastructure/database/queries/intelligence/comparison_queries.py
```

### Business Logic
```
OLD: business/business_modules/intelligence.py
NEW: core/use_cases/intelligence/get_exclusivity.py
     core/use_cases/intelligence/catalog_similarity.py
     core/use_cases/intelligence/compare_regions.py
```

### Graphs
```
OLD: business/graph_core/
     business/nodes/
NEW: graphs/business/graph.py
     graphs/business/supervisor.py
     graphs/business/nodes/
```

### Routing
```
OLD: main_router/advanced_router.py
     main_router/validation_preprocessor.py
NEW: routing/advanced_router.py
     routing/validation_preprocessor.py
```

## Migration Order

1. ✅ Phase 1: Prompts (no dependencies)
2. ✅ Phase 2: Cache (single dependency)
3. ✅ Phase 3: Validators (few dependencies)
4. ⚠️ Phase 4: Queries (SQL only)
5. ⚠️ Phase 5: Use Cases (business logic)
6. ⚠️ Phase 6: Graphs (final migration)
