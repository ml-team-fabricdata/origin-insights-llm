# =============================================================================
# STANDARD LIBRARY IMPORTS
# =============================================================================
import json
import logging
import re
import unicodedata as ud
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

# =============================================================================
# THIRD PARTY IMPORTS
# =============================================================================
from langchain_core.tools import StructuredTool, Tool
from rapidfuzz import fuzz, process

# =============================================================================
# LOCAL IMPORTS
# =============================================================================
from src.sql.utils.sql_db import db

# =============================================================================
# LOGGER
# =============================================================================
logger = logging.getLogger(__name__)

# =============================================================================
# TYPE ALIASES
# =============================================================================
NumberOrStr = Union[int, float, str, None]