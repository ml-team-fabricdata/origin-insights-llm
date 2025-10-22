# Source Code Directory Structure

This document provides an overview of the src directory structure and its components, with a focus on organization and avoiding redundancy.


## Project Organization

### Main Components
```
src/
├── data/                  # Reference data files (JSONL)
│   ├── currency.jsonl
│   ├── platform_name_iso.jsonl
│   ├── platform_name.jsonl
│   ├── primary_country.jsonl
│   └── primary_genre.jsonl
├── embedding/             # Embedding models and operations
├── prompt_templates/      # Prompt templates and configurations
│   └── prompt.py
├── sql/                   # Main SQL and database logic
│   ├── __init__.py
│   ├── modules/           # Domain modules (business logic)
│   │   ├── business/      # Business analytics, pricing, rankings
│   │   │   ├── intelligence.py    # Market analysis, catalog comparisons
│   │   │   ├── pricing.py         # Price queries, stats, changes
│   │   │   └── rankings.py        # Genre momentum, top content
│   │   ├── common/        # Shared logic (admin, validation)
│   │   │   ├── admin.py           # SQL builder, executor, system management
│   │   │   └── validation.py      # Title, actor, director validation
│   │   ├── content/       # Content discovery and metadata
│   │   │   ├── discovery.py       # Filmography, ratings
│   │   │   └── metadata.py        # Metadata queries, counts, lists
│   │   ├── platform/      # Platform availability and presence
│   │   │   ├── availability.py    # Availability by UID, exclusives, premieres
│   │   │   └── presence.py        # Presence queries, counts, distinct values
│   │   └── talent/        # Talent (actors, directors, collaborations)
│   │       ├── actors.py          # Actor filmography, co-actors
│   │       ├── directors.py       # Director filmography, collaborators
│   │       └── collaborations.py  # Actor-director common projects
│   ├── queries/           # Centralized SQL query templates
│   │   ├── business/
│   │   │   ├── intelligence_queries.py
│   │   │   ├── pricing_queries.py
│   │   │   └── rankings_queries.py
│   │   ├── common/
│   │   │   └── queries_validation.py
│   │   ├── content/
│   │   │   ├── queries_discovery.py
│   │   │   └── queries_metadata.py
│   │   ├── platform/
│   │   │   ├── queries_availability.py
│   │   │   └── queries_presence.py
│   │   └── talent/
│   │       ├── queries_actors.py
│   │       ├── queries_directors.py
│   │       └── queries_collaborations.py
│   ├── tools/             # LangChain tool wrappers for each domain
│   │   ├── all_tools.py           # Aggregates all tools
│   │   ├── business/
│   │   │   ├── intelligence_tools.py
│   │   │   ├── pricing_tools.py
│   │   │   └── rankings_tools.py
│   │   ├── common/
│   │   │   ├── admin_tools.py
│   │   │   └── validation_tools.py
│   │   ├── content/
│   │   │   ├── discovery_tools.py
│   │   │   └── metadata_tools.py
│   │   ├── platform/
│   │   │   ├── availability_tools.py
│   │   │   └── presence_tools.py
│   │   └── talent/
│   │       ├── actors_tools.py
│   │       ├── directors_tools.py
│   │       └── collaborations_tools.py
│   └── utils/             # Shared utilities
│       ├── constants_sql.py       # DB tables, limits, regions, policies
│       ├── db_utils_sql.py        # Query helpers, fuzzy matching, validation
│       ├── default_import.py      # Common imports
│       ├── sql_db.py              # DB connection manager
│       └── validators_shared.py   # Country/platform/region resolvers
└── __init__.py
```


## SQL Module Documentation

### Common Module (`sql/modules/common/`)

**validation.py**
- Title, actor, and director validation
- Exact and fuzzy matching with RapidFuzz
- Similarity scoring and ambiguity resolution
- Functions: `validate_title()`, `validate_actor()`, `validate_director()`

**admin.py**
- SQL query builder and executor
- System management and administrative operations
- Dynamic SQL generation with safety checks
- Functions: `build_sql()`, `run_sql()`

### Business Module (`sql/modules/business/`)

**intelligence.py**
- Market analysis and catalog comparisons
- Platform exclusivity analysis by country
- Catalog similarity between platforms
- Content gap analysis (titles in A not in B)
- Functions: `platform_exclusivity_country()`, `catalog_similarity()`, `titles_in_A_not_in_B_sql()`

**pricing.py**
- Price queries with latest, history, and changes tracking
- Price statistics (min, max, avg, median, percentiles)
- Presence with price information (JOIN with prices table)
- Hits with quality filters (definition, license)
- Functions: `query_presence_with_price()`, `tool_prices_latest()`, `tool_prices_history()`, `tool_prices_changes_last_n_days()`, `tool_prices_stats()`, `tool_hits_with_quality()`

**rankings.py**
- Genre momentum analysis (growth comparison between periods)
- Top content by presence or global hits
- Rolling window calculations for time-based rankings
- Functions: `get_genre_momentum()`, `top_by_uid()`, `compute_window_anchored_to_table()`

### Content Module (`sql/modules/content/`)

**discovery.py**
- Content filmography by UID
- Title ratings and popularity metrics
- Functions: `get_filmography_by_uid()`, `get_title_rating()`

**metadata.py**
- Metadata queries with flexible filtering
- Count, list, and distinct value queries
- Support for type, year, genre, language, country filters
- Functions: `query_metadata_count()`, `query_metadata_list()`, `query_metadata_distinct()`

### Platform Module (`sql/modules/platform/`)

**availability.py**
- Content availability by UID with country/region support
- **NEW: Region support (LATAM, EU, etc.) - expands to multiple countries**
- Platform exclusives by country
- Recent premieres by country (last 7 days)
- Price information integration (optional)
- Functions: `get_availability_by_uid()`, `query_platforms_for_uid_by_country()`, `get_platform_exclusives()`, `get_recent_premieres_by_country()`

**presence.py**
- Presence queries with count, list, and distinct operations
- Platform and country filtering
- Active/inactive presence tracking
- Functions: `query_presence_count()`, `query_presence_list()`, `query_presence_distinct()`

### Talent Module (`sql/modules/talent/`)

**actors.py**
- Actor filmography by name or ID
- Co-actors analysis (actors who worked together)
- **Validation: Checks if actor exists before querying**
- Functions: `get_actor_filmography()`, `get_actor_filmography_by_name()`, `get_actor_coactors()`, `get_actor_coactors_by_name()`

**directors.py**
- Director filmography by name or ID
- Director collaborators (co-directors on same films)
- **Validation: Checks if director exists before querying**
- Functions: `get_director_filmography()`, `get_director_filmography_by_name()`, `get_director_collaborators()`

**collaborations.py**
- Common projects between actors and directors
- Collaboration analysis by IDs or names
- Functions: `get_common_projects_actor_director()`, `get_common_projects_actor_director_by_name()`

### Utility Modules (`sql/utils/`)

**constants_sql.py**
- Database schemas and table names (`META_TBL`, `PRES_TBL`, `PRICES_TBL`, `HITS_PRESENCE_TBL`, etc.)
- Query defaults and limits (`DEFAULT_LIMIT`, `MAX_LIMIT`, `DEFAULT_DAYS_BACK`)
- Fuzzy search configuration (`FUZZY_THRESHOLD`, `MAX_CANDIDATES`)
- Column whitelists by table (for security)
- Content definitions and licenses (`VALID_DEFINITIONS`, `VALID_LICENSES`)
- **Geographical regions** (`REGION_TO_ISO2`, `REGION_ALIASES`) - LATAM, EU, Asia, etc.
- System policies and validation rules

**db_utils_sql.py**
- Input validation functions (`validate_limit()`, `validate_days_back()`, `normalize_input()`)
- Text processing and normalization (`normalize()`, `clean_text()`)
- **Fuzzy matching with RapidFuzz** (`best_match_rapidfuzz()`, `resolve_value_rapidfuzz()`)
- CJK-aware tokenization for multilingual support
- Date and time functions (`get_date_range()`, `parse_time_to_days()`)
- Data handling functions (`handle_query_result()`, `format_validation_options()`)
- SQL helpers (`build_like_pattern()`, `build_in_clause()`)

**validators_shared.py**
- Country and platform resolution (`resolve_country_iso()`, `resolve_platform_name()`)
- **Region to ISO list conversion** (`get_region_iso_list()`, `resolve_region_isos()`)
- UID and country parsing (`parse_uid_with_country()`)
- Validation data caching for performance

**sql_db.py**
- PostgreSQL connection manager (`SQLConnectionManager`)
- AWS Secrets Manager integration for credentials
- Connection pooling and retry logic
- Query execution with error handling
- Functions: `get_secret()`, `execute_query()`

**default_import.py**
- Common imports for all modules
- Standard library imports (json, logging, datetime, etc.)
- Third-party imports (RapidFuzz, psycopg2, etc.)
- Type hints and typing utilities

## Tools Layer (`sql/tools/`)

The tools layer provides LangChain-compatible wrappers for all SQL functions, enabling easy integration with LLM agents.

### Tool Organization

**all_tools.py**
- Aggregates all tools from all domains
- Exports: `ALL_SQL_TOOLS`, `ALL_BUSINESS_TOOLS`, `ALL_CONTENT_TOOLS`, `ALL_PLATFORM_TOOLS`, `ALL_TALENT_TOOLS`, `ALL_COMMON_TOOLS`
- Total: ~40+ tools available

### Tool Categories

**Business Tools** (`business/`)
- `intelligence_tools.py`: Platform exclusivity, catalog similarity, gap analysis
- `pricing_tools.py`: Price queries, stats, changes, hits with quality
- `rankings_tools.py`: Genre momentum, top content rankings

**Common Tools** (`common/`)
- `admin_tools.py`: SQL builder and executor for dynamic queries
- `validation_tools.py`: Title, actor, director validation

**Content Tools** (`content/`)
- `discovery_tools.py`: Filmography, ratings
- `metadata_tools.py`: Metadata count, list, distinct queries

**Platform Tools** (`platform/`)
- `availability_tools.py`: Availability by UID (with region support), exclusives, premieres
- `presence_tools.py`: Presence count, list, distinct queries

**Talent Tools** (`talent/`)
- `actors_tools.py`: Actor filmography, co-actors
- `directors_tools.py`: Director filmography, collaborators
- `collaborations_tools.py`: Actor-director common projects

### Tool Features

- **Type Safety**: All tools use `StructuredTool` or `Tool.from_function()` with proper schemas
- **Error Handling**: Consistent error messages and validation
- **Documentation**: Each tool has detailed descriptions for LLM understanding
- **Region Support**: Platform tools support both individual countries and regions (LATAM, EU, etc.)

## Queries Layer (`sql/queries/`)

Centralized SQL query templates organized by domain. Each query file contains parameterized SQL strings using f-strings and placeholders.

### Query Organization

**business/**
- `intelligence_queries.py`: Market analysis queries
- `pricing_queries.py`: Price-related queries with JOINs
- `rankings_queries.py`: Genre momentum, top content, max date queries

**common/**
- `queries_validation.py`: Title, actor, director search queries (exact and fuzzy)

**content/**
- `queries_discovery.py`: Filmography and rating queries
- `queries_metadata.py`: Metadata queries with flexible filtering

**platform/**
- `queries_availability.py`: Availability queries with/without prices
- `queries_presence.py`: Presence queries with various aggregations

**talent/**
- `queries_actors.py`: Actor filmography and co-actors queries
- `queries_directors.py`: Director filmography and collaborators queries
- `queries_collaborations.py`: Actor-director collaboration queries

### Query Features

- **Parameterized**: Use `%s` placeholders for safe parameter binding
- **Template Strings**: Use f-strings for table names from `constants_sql.py`
- **Flexible Filtering**: Support dynamic WHERE clauses via `{placeholder}` format
- **Performance**: Optimized with proper JOINs, indexes, and LIMIT clauses

## Key Features

### 🔍 Data Validation
The system includes robust validation for:
- **Titles**: Exact and fuzzy matching with similarity scoring
- **Actors**: Name validation with disambiguation
- **Directors**: Name validation with title count ranking
- **Countries**: ISO-2 code resolution with fuzzy matching
- **Platforms**: Platform name normalization and validation
- **Regions**: Support for LATAM, EU, Asia, and other multi-country regions

### 🗄️ Database Operations
- **Connection Management**: PostgreSQL with AWS Secrets Manager integration
- **Query Organization**: Centralized SQL templates by domain
- **Safety**: Parameterized queries, column whitelists, input sanitization
- **Performance**: Connection pooling, retry logic, optimized queries
- **Multilingual**: CJK-aware text processing and tokenization

### 📊 Content Management
- **Discovery**: Filmography by UID, title ratings, popularity metrics
- **Metadata**: Flexible filtering by type, year, genre, language, country
- **Availability**: Platform availability with country/region support
- **Presence**: Active/inactive tracking, platform distribution analysis

### 💼 Business Intelligence
- **Pricing**: Latest prices, history, changes, statistics (min/max/avg/median/percentiles)
- **Rankings**: Genre momentum, top content by presence or global hits
- **Intelligence**: Platform exclusivity, catalog similarity, content gap analysis
- **Quality Filters**: Hits with definition (4K/HD/SD) and license (EST/VOD) filters

### 🎭 Talent Analysis
- **Actors**: Filmography, co-actors who worked together
- **Directors**: Filmography, co-directors on same films
- **Collaborations**: Common projects between actors and directors
- **Validation**: Existence checks before querying to provide helpful error messages

### 🌍 Region Support (NEW)
- **Multi-Country Queries**: Single parameter expands to multiple countries
- **Supported Regions**: 
  - LATAM/latin_america (20+ countries)
  - EU (27 countries)
  - Europe, Asia, Africa, Oceania
  - North/South/Central America
  - Middle East, Caribbean
- **Automatic Expansion**: `country="LATAM"` → queries all Latin American countries
- **Backward Compatible**: Still supports individual country codes (US, AR, BR, etc.)

## Architecture Patterns

### Separation of Concerns
- **Queries**: Pure SQL templates (no business logic)
- **Modules**: Business logic and data processing
- **Tools**: LangChain wrappers for LLM integration
- **Utils**: Shared utilities and helpers

### Error Handling
- Consistent error message format
- Validation before expensive queries
- Helpful suggestions when entities not found
- Graceful degradation for missing data

### Code Reuse
- Shared validation logic in `validators_shared.py`
- Common query patterns in `db_utils_sql.py`
- Centralized constants in `constants_sql.py`
- Default imports in `default_import.py`

