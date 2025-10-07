"""Fallback build metadata snapshot.

This module is overwritten during Docker image builds to bake the latest build
information directly into the artifact.  Keeping a placeholder in source control
ensures imports keep working in development and when building without metadata.
"""

BUILD_SNAPSHOT: dict[str, str] = {
    "sha": "unknown",
    "ref": "unknown",
    "time": "unknown",
}
