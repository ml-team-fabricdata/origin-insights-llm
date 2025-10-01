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
│   ├── core/              # Core system logic (validation, admin, queries)
│   │   ├── admin.py
│   │   ├── validation.py
│   │   ├── queries.py
│   │   └── ...
│   ├── modules/           # Domain modules
│   │   ├── business/      # Business analytics, pricing, rankings
│   │   │   ├── intelligence.py
│   │   │   ├── pricing.py
│   │   │   ├── rankings.py
│   │   │   └── ...
│   │   ├── common/        # Shared logic (admin, query detection, validation)
│   │   │   ├── admin.py
│   │   │   ├── query_detection.py
│   │   │   ├── query_handler.py
│   │   │   ├── validation.py
│   │   │   └── ...
│   │   ├── content/       # Content discovery and metadata
│   │   │   ├── discovery.py
│   │   │   ├── metadata.py
│   │   │   └── ...
│   │   ├── platform/      # Platform availability and presence
│   │   │   ├── availability.py
│   │   │   ├── presence.py
│   │   │   └── ...
│   │   ├── talent/        # Talent (actors, directors, collaborations)
│   │   │   ├── actors.py
│   │   │   ├── directors.py
│   │   │   ├── collaborations.py
│   │   │   └── ...
│   ├── queries/           # Centralized SQL query templates
│   │   ├── business/
│   │   ├── common/
│   │   ├── content/
│   │   ├── platform/
│   │   ├── talent/
│   │   └── ...
│   ├── tools/             # Tool wrappers for each domain
│   │   ├── all_tools.py
│   │   ├── business/
│   │   ├── common/
│   │   ├── content/
│   │   ├── platform/
│   │   ├── talent/
│   │   └── ...
│   ├── utils/             # Shared utilities
│   │   ├── constants_sql.py
│   │   ├── db_utils_sql.py
│   │   ├── default_import.py
│   │   ├── sql_db.py
│   │   ├── table_constants.py
│   │   ├── validators_shared.py
│   │   └── ...
│   └── __init__.py
└── __init__.py
```


## SQL Module Documentation

### Core Module (`sql/core/`)

**validation.py**
- Title, actor, and director validation (exact/fuzzy matching, similarity, count-based)

**admin.py**
- System management, administrative operations

**queries.py**
- Centralized query logic for core system operations

### Business Module (`sql/modules/business/`)

**intelligence.py**
- Market analysis, performance metrics, business insights

**pricing.py**
- Price analysis, strategy, market rate comparisons

**rankings.py**
- Content and platform rankings, popularity metrics

### Content Module (`sql/modules/content/`)

**discovery.py**
- Content recommendation, similarity search, topic-based queries

**metadata.py**
- Metadata extraction, processing, standardization

### Platform Module (`sql/modules/platform/`)

**availability.py**
- Content availability by ID, summary formatting, platform checks

**presence.py**
- Content presence verification, coverage analysis, distribution tracking

### Talent Module (`sql/modules/talent/`)

**actors.py**
- Actor lookup, validation, filmography, performance tracking

**directors.py**
- Director validation, filmography, project management

**collaborations.py**
- Actor-director partnerships, team analytics, project connections

### Utility Modules (`sql/utils/`)

**db_utils_sql.py**
- Core DB functions, connection pool, query execution

**constants_sql.py**
- Query templates, DB configs, system parameters

**validators_shared.py**
- Input sanitization, data validation, format verification

**default_import.py, sql_db.py, table_constants.py**
- Shared imports, DB logic, table constants

## Directory Structure


### Core Components

#### `/sql` - SQL Related Modules
Organized for code reuse and minimal redundancy:

**core/**
- `admin.py`: Administrative operations and system management
- `validation.py`: Central validation logic for all entities
- `queries.py`: Core system queries and logic

**modules/**
- `business/`: Business analytics, pricing, and rankings
- `common/`: Shared admin, query detection, and validation
- `content/`: Content discovery and metadata
- `platform/`: Platform availability and presence
- `talent/`: Actor, director, and collaboration management

**queries/**
- Centralized SQL query templates, organized by domain (business, content, platform, talent)

**tools/**
- Tool wrappers for each domain, enabling modular access to business, content, platform, and talent logic

**utils/**
- Shared utilities for database operations, validation, constants, and configuration

**data/**
- Reference data files in JSONL format for currencies, platforms, countries, genres

**embedding/**
- Embedding models and related operations

**prompt_templates/**
- Prompt templates and configuration for LLMs and automation

#### `/data` - Data Files
Contains essential data files in JSONL format:
- `currency.jsonl` - Currency reference data
- `platform_name_iso.jsonl` - Platform names with ISO codes
- `platform_name.jsonl` - Platform naming references
- `primary_country.jsonl` - Country reference data
- `primary_genre.jsonl` - Genre classification data

#### `/embedding` 
Directory for embedding-related operations and models

#### `/prompt_templates`
- `prompt.py` - Contains prompt templates and configurations

### Utility Components

#### Shared Utilities (`/sql/utils/`)
Centralized utilities to avoid code duplication:

- **Database Operations**
  - `db_utils.py` - Connection management and query execution
  - `sql_db.py` - Core database operations
  - `connection_pool.py` - Database connection pooling

- **Validation & Processing**
  - `validators.py` - Common validation functions
  - `formatters.py` - Data formatting utilities
  - `sanitizers.py` - Input sanitization

- **Configuration**
  - `constants.py` - System-wide constants
  - `config.py` - Configuration management
  - `defaults.py` - Default settings and imports

## Key Features

### Data Validation
The system includes robust validation for:
- Directors and actors
- Content titles
- Platform availability
- Business intelligence data

### Database Operations
- Structured query organization by domain
- Utility functions for database operations
- Connection management and pooling

### Content Management
- Content discovery and recommendations
- Metadata handling
- Availability tracking across platforms

### Business Intelligence
- Pricing analysis
- Rankings and performance metrics
- Analytics and reporting tools

