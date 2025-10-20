"""
DEPRECATED: This module has been renamed to param_validation_node.py

Please update your imports:
  from src.strands.utils.validation_node import validation_node
  →
  from src.strands.utils.param_validation_node import validation_node

This compatibility wrapper will be removed in a future version.
"""

import warnings

# Re-export everything from the new module
from src.strands.utils.param_validation_node import (
    ValidationResult,
    validate_and_normalize_fields,
    validation_node,
    create_validation_edge
)

# Emit deprecation warning
warnings.warn(
    "validation_node.py is deprecated. Use param_validation_node.py instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "ValidationResult",
    "validate_and_normalize_fields",
    "validation_node",
    "create_validation_edge"
]
