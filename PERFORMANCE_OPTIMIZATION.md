# Performance Optimization Guide

## Current Performance Issues

### Observed Slow Queries:
1. **`validate_title`**: ~8 seconds (should be <1s)
2. **`get_title_rating`**: ~17 seconds (should be <3s)
3. **`get_actor_filmography`**: ~22 seconds (should be <5s)
4. **`get_actor_coactors`**: ~24 seconds (should be <5s)
5. **`get_director_filmography`**: ~22 seconds (should be <5s)
6. **`get_director_collaborators`**: ~22 seconds (should be <5s)

## Important Note About Views

⚠️ **`ms.metadata_simple_all` is a VIEW, not a table.**

You **cannot create indexes directly on views**. Instead, you need to:

1. **Option 1 (Recommended)**: Create indexes on the **base tables** that compose the view
2. **Option 2**: Convert the view to a **materialized view** and create indexes on it

### Step 1: Find the base table(s)

Run this query in PostgreSQL to see what tables the view uses:

```sql
-- Check the view definition
SELECT definition 
FROM pg_views 
WHERE schemaname = 'ms' AND viewname = 'metadata_simple_all';
```

The result will show you the SQL that creates the view. Look for table names in the `FROM` clause.

**Common possibilities:**
- `ms.new_cp_metadata_estandar` (most likely based on constants_sql.py)
- A join of multiple tables
- Another view (in which case, check that view's definition too)

### Step 2: Replace placeholders in the index commands

Once you identify the base table (let's say it's `ms.new_cp_metadata_estandar`), replace all instances of `base_table_name` in the commands below with the actual table name.

## Required Database Indexes

**IMPORTANT**: Replace `ms.metadata_simple_all` with the actual base table name(s) in the commands below.

Run these SQL commands in PostgreSQL to create the necessary indexes:

```sql
-- ============================================================================
-- CRITICAL INDEXES (Apply these first for immediate improvement)
-- ============================================================================

-- For validate_title (exact and fuzzy searches)
-- REPLACE 'base_table_name' with the actual base table from the view definition
CREATE INDEX IF NOT EXISTS idx_meta_title_lower 
    ON base_table_name (LOWER(title));

-- Enable trigram extension for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_meta_title_trgm 
    ON base_table_name USING gin (title gin_trgm_ops);

-- For get_title_rating (joins on uid)
CREATE INDEX IF NOT EXISTS idx_hits_global_uid 
    ON ms.hits_global (uid);

CREATE INDEX IF NOT EXISTS idx_hits_presence_uid 
    ON ms.hits_presence (uid);

CREATE INDEX IF NOT EXISTS idx_meta_uid 
    ON base_table_name (uid);

-- ============================================================================
-- IMPORTANT INDEXES (For actor/director queries)
-- ============================================================================

-- For actor filmography and coactors
CREATE INDEX IF NOT EXISTS idx_acted_in_cast_id 
    ON ms.acted_in (cast_id);

CREATE INDEX IF NOT EXISTS idx_acted_in_uid 
    ON ms.acted_in (uid);

-- Composite index for better join performance
CREATE INDEX IF NOT EXISTS idx_acted_in_cast_uid 
    ON ms.acted_in (cast_id, uid);

-- For director filmography and collaborators
CREATE INDEX IF NOT EXISTS idx_directed_by_crew_id 
    ON ms.directed_by (crew_id);

CREATE INDEX IF NOT EXISTS idx_directed_by_uid 
    ON ms.directed_by (uid);

-- Composite index for better join performance
CREATE INDEX IF NOT EXISTS idx_directed_by_crew_uid 
    ON ms.directed_by (crew_id, uid);

-- For cast/crew lookups
CREATE INDEX IF NOT EXISTS idx_cast_name_lower 
    ON ms.cast (LOWER(name));

CREATE INDEX IF NOT EXISTS idx_crew_name_lower 
    ON ms.crew (LOWER(name));

-- ============================================================================
-- OPTIONAL INDEXES (For additional performance)
-- ============================================================================

-- For availability queries
CREATE INDEX IF NOT EXISTS idx_presence_uid 
    ON ms.new_cp_presence (uid);

CREATE INDEX IF NOT EXISTS idx_presence_platform 
    ON ms.new_cp_presence (platform_name);

CREATE INDEX IF NOT EXISTS idx_presence_iso 
    ON ms.new_cp_presence (iso_alpha2);

-- For pricing queries
CREATE INDEX IF NOT EXISTS idx_prices_hash 
    ON ms.new_cp_presence_prices (hash_unique);

CREATE INDEX IF NOT EXISTS idx_prices_created 
    ON ms.new_cp_presence_prices (created_at DESC);

-- ============================================================================
-- ANALYZE TABLES (Run after creating indexes)
-- ============================================================================

ANALYZE base_table_name;  -- Replace with actual base table
ANALYZE ms.hits_global;
ANALYZE ms.hits_presence;
ANALYZE ms.acted_in;
ANALYZE ms.directed_by;
ANALYZE ms.cast;
ANALYZE ms.crew;
ANALYZE ms.new_cp_presence;
ANALYZE ms.new_cp_presence_prices;
```

## Expected Performance Improvements

After applying indexes:

| Query | Before | After | Improvement |
|-------|--------|-------|-------------|
| `validate_title` | ~8s | ~0.5s | **94%** |
| `get_title_rating` | ~17s | ~1-2s | **88-94%** |
| `get_actor_filmography` | ~22s | ~2-3s | **86-91%** |
| `get_actor_coactors` | ~24s | ~3-5s | **79-88%** |
| `get_director_filmography` | ~22s | ~2-3s | **86-91%** |
| `get_director_collaborators` | ~22s | ~3-5s | **79-88%** |

**Total query time for "Inception"**: From ~61s to **~8-12s** (80-87% faster)

## Code Optimizations Already Applied

1. ✅ Fixed `get_title_rating` GROUP BY bug (removed `h.hits` from GROUP BY)
2. ✅ Added `limit` parameter to `get_availability_by_uid` (default 100)
3. ✅ Added `limit` parameters to actor/director functions with documentation
4. ✅ Fixed `tool_metadata_count` KeyError bug
5. ✅ Updated tool descriptions to suggest lower limits for faster responses

## Additional Recommendations

### 1. Enable Query Caching (Optional)
Consider implementing a simple in-memory cache for frequently accessed data:
- Popular titles (e.g., "Inception", "The Dark Knight")
- Popular actors (e.g., "Brad Pitt", "Leonardo DiCaprio")
- Popular directors (e.g., "Christopher Nolan", "Steven Spielberg")

### 2. Connection Pooling
Ensure your database connection uses connection pooling to reduce connection overhead.

### 3. Query Monitoring
Use PostgreSQL's `pg_stat_statements` extension to monitor slow queries:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slowest queries
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### 4. Regular Maintenance
Run these commands periodically:

```sql
-- Update statistics
ANALYZE;

-- Rebuild indexes if needed
REINDEX DATABASE your_database_name;

-- Vacuum to reclaim space
VACUUM ANALYZE;
```

## Verification

After applying indexes, test with:

```python
# Test validate_title
from src.sql.modules.common.validation import validate_title
import time

start = time.time()
result = validate_title("Inception")
print(f"validate_title took {time.time() - start:.2f}s")

# Test get_title_rating
from src.sql.modules.content.discovery import get_title_rating

start = time.time()
result = get_title_rating("16c0c6e7ecbeec8e66f472f27852804b")
print(f"get_title_rating took {time.time() - start:.2f}s")
```

Expected results after indexes:
- `validate_title`: < 1 second
- `get_title_rating`: < 2 seconds
