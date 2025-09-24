# Source Code Directory Structure

This document provides an overview of the src directory structure and its components, with a focus on organization and avoiding redundancy.

## Project Organization

### Main Components
```
src/
├── sql/                  # SQL and Database Operations
│   ├── core/            # Core functionality
│   ├── modules/         # Domain-specific modules
│   ├── queries/         # Centralized SQL queries
│   └── utils/           # Shared utilities
├── data/                # Reference data files
├── embedding/           # Embedding operations
└── prompt_templates/    # Prompt configurations
```

## SQL Module Documentation

### Core Module (`sql/core/`)

#### Validation (`validation.py`)
- `validate_title(title: str, threshold: Optional[float])` - Validates movie/TV show titles with exact and fuzzy matching
- `validate_actor(name: Union[str, List[str], Any], threshold: Optional[float])` - Validates actor names with similarity matching
- `validate_director(name: Union[str, List[str], Any], threshold: Optional[float])` - Validates director names with title count consideration
- `search_title_exact(title: str)` - Performs exact title search in the database
- `search_title_fuzzy(title: str, threshold: float, limit: int)` - Performs fuzzy title search with configurable parameters

#### Queries (`queries.py`)
Core SQL queries and database operations for the main functionality of the system.

### Business Module (`sql/business/`)

#### Intelligence (`intelligence.py`)
Business intelligence and analytics functions:
- Market analysis
- Performance metrics
- Business insights queries

#### Pricing (`pricing.py`)
Pricing-related operations:
- Price analysis
- Pricing strategy queries
- Market rate comparisons

#### Rankings (`rankings.py`)
Content and performance ranking operations:
- Content performance metrics
- Platform rankings
- Popularity metrics

### Content Module (`sql/content/`)

#### Discovery (`discovery.py`)
Content discovery operations:
- Content recommendation algorithms
- Similar content search
- Topic-based content search

#### Metadata (`metadata.py`)
Content metadata operations:
- Metadata extraction and processing
- Content information management
- Data standardization functions

### Platform Module (`sql/platform/`)

#### Availability (`availability.py`)
Key functions:
- `fetch_availability_by_uid(uid: str, iso2: Optional[str], with_prices: bool)` - Gets content availability by ID
- `render_availability_summary(rows: List[Dict], country_pretty: str, with_prices: bool)` - Formats availability data
- Platform-specific availability checks

#### Presence (`presence.py`)
Platform presence validation:
- Content presence verification
- Platform coverage analysis
- Distribution tracking

### Talent Module (`sql/talent/`)

#### Actors (`actors.py`)
Actor-related operations:
- Actor lookup and validation
- Filmography queries
- Performance tracking

#### Directors (`directors.py`)
Director-related operations:
- Director validation
- Filmography management
- Project tracking

#### Collaborations (`collaborations.py`)
Collaboration analysis:
- Actor-director partnerships
- Team analytics
- Project connections

### Utility Modules (`sql/utils/`)

#### Database Utilities (`db_utils_sql.py`)
Core database functions:
- `run_sql(sql: str, params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]])` - Executes SQL queries safely
- Connection pool management
- Query execution handlers

#### Constants (`constants_sql.py`)
SQL-related constants:
- Query templates
- Database configurations
- System parameters

#### Validators (`validators_shared.py`)
Shared validation utilities:
- Input sanitization
- Data validation
- Format verification

## Directory Structure

### Core Components

#### `/sql` - SQL Related Modules
The SQL directory is organized to maximize code reuse and minimize redundancy:

##### Core Module
- **core/**
  - `admin.py` - Administrative operations and system management
  - `validation.py` - Central validation logic for all entities
  - `queries.py` - Core system SQL queries

##### Domain-Specific Modules
- **business/**
  - `intelligence.py` - Business analytics and insights
  - `pricing.py` - Pricing analysis and strategies
  - `rankings.py` - Performance metrics and rankings

- **content/**
  - `discovery.py` - Content recommendation engine
  - `metadata.py` - Content information management

- **platform/**
  - `availability.py` - Content availability services
  - `presence.py` - Platform presence tracking

- **talent/**
  - `actors.py` - Actor management and tracking
  - `directors.py` - Director information handling
  - `collaborations.py` - Talent relationship analysis

##### Shared Components
- **utils/**
  - `db_utils.py` - Database operations and connection management
  - `validators.py` - Common validation utilities
  - `constants.py` - System-wide constants

##### Query Management
- **queries/**
  - Centralized location for all SQL queries
  - Organized by domain (business, content, platform, talent)
  - Reduces query duplication across modules

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

## Usage

Each module is designed to be imported and used independently while maintaining integration with the overall system. For example:

```python
from src.sql.modules.common.validation import validate_director
from src.sql.modules.content.discovery import discover_content
from src.sql.modules.business.pricing import analyze_pricing
```

For more specific implementation details, refer to the individual module docstrings and comments.