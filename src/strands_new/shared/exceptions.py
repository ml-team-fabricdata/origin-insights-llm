"""Custom exceptions."""


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class CacheError(Exception):
    """Raised when cache operation fails."""
    pass


class DatabaseError(Exception):
    """Raised when database operation fails."""
    pass


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass
