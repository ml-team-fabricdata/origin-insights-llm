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

from langchain_core.tools import StructuredTool, Tool
from rapidfuzz import fuzz, process

from app.strands.infrastructure.database.connection import db

logger = logging.getLogger(__name__)

NumberOrStr = Union[int, float, str, None]
