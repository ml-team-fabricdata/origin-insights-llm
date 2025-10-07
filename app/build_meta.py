"""Utilities for build metadata injected at image build time.

The GitHub Actions workflow populates ``BUILD_SHA``, ``BUILD_REF`` and
``BUILD_TIME`` as build arguments when baking the Docker image.  App Runner will
then expose them as environment variables at runtime.  Centralising the logic
for reading and shaping these values makes it easier to reuse from different
routers and to add debugging information when something goes wrong (for
instance, when ``/version`` keeps returning ``"unknown"`` during deployments).

In App Runner we noticed sporadic situations where the environment variables are
temporarily unavailable when the process starts.  To make the automation more
robust we also persist the metadata to a JSON file during the Docker build and
fall back to that snapshot if needed.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass

try:  # pragma: no cover - extremely defensive
    from app._build_meta_snapshot import BUILD_SNAPSHOT
except Exception:  # noqa: BLE001 - best effort fallback
    BUILD_SNAPSHOT = {
        "sha": "unknown",
        "ref": "unknown",
        "time": "unknown",
    }

@dataclass(frozen=True)
class BuildMeta:
    """Container build metadata.

    ``short_sha`` replicates what GitHub logs print (first seven chars) so that
    the automation waiting on App Runner can match either the full SHA or the
    shortened form.  ``source`` is purely informational so operators can double
    check if the values came from environment variables or defaults.
    """

    sha: str
    short_sha: str
    ref: str
    time: str
    source: str

    def as_dict(self) -> dict[str, str]:
        """Return a serialisable representation for JSON responses."""

        return {
            "sha": self.sha,
            "short": self.short_sha,
            "ref": self.ref,
            "time": self.time,
            "source": self.source,
        }


def _clean(value: str | None) -> str:
    """Strip whitespace and fall back to ``"unknown"``."""

    if value is None:
        return "unknown"
    cleaned = value.strip()
    return cleaned if cleaned else "unknown"


def get_build_meta() -> BuildMeta:
    """Collect build metadata from environment variables.

    ``BUILD_SHA`` contains the commit that triggered the image build.  If it is
    missing we keep the ``unknown`` placeholder – useful to quickly detect that
    the pipeline did not inject the build args (the typical cause behind the
    repeated ``{"build":"unknown"}`` responses seen in App Runner health checks).
    """

    # 1) collect from environment ------------------------------------------
    sha = _clean(os.getenv("BUILD_SHA"))
    ref = _clean(os.getenv("BUILD_REF"))
    time = _clean(os.getenv("BUILD_TIME"))

    source_parts: list[str] = []
    if any(v != "unknown" for v in (sha, ref, time)):
        source_parts.append("env")

    # 2) fallback to persisted file ----------------------------------------
    meta_path = os.getenv("BUILD_META_FILE")
    if meta_path:
        candidate_paths = [Path(meta_path)]
    else:
        candidate_paths = [
            Path(__file__).resolve().parent.parent / ".build-meta.json",
            Path("/.build-meta.json"),
        ]

    loaded = {}
    for path in candidate_paths:
        try:
            with path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh) or {}
        except FileNotFoundError:
            continue
        except Exception:
            # Ignore malformed files – we just fall back to env defaults.
            continue
        if loaded:
            source_parts.append(f"file:{path.name}")
            loaded_sha = _clean(str(loaded.get("sha")))
            loaded_ref = _clean(str(loaded.get("ref")))
            loaded_time = _clean(str(loaded.get("time")))
            if sha == "unknown":
                sha = loaded_sha
            if ref == "unknown":
                ref = loaded_ref
            if time == "unknown":
                time = loaded_time
            break

    # 3) fallback to baked snapshot module --------------------------------
    snapshot_used = False
    snapshot_sha = _clean(str(BUILD_SNAPSHOT.get("sha")))
    snapshot_ref = _clean(str(BUILD_SNAPSHOT.get("ref")))
    snapshot_time = _clean(str(BUILD_SNAPSHOT.get("time")))

    if sha == "unknown" and snapshot_sha != "unknown":
        sha = snapshot_sha
        snapshot_used = True
    if ref == "unknown" and snapshot_ref != "unknown":
        ref = snapshot_ref
        snapshot_used = True
    if time == "unknown" and snapshot_time != "unknown":
        time = snapshot_time
        snapshot_used = True

    if snapshot_used:
        source_parts.append("module")

    short_sha = sha[:7] if sha not in {"", "unknown"} else "unknown"

    if not source_parts:
        source = "default"
    else:
        source = "+".join(dict.fromkeys(source_parts))  # preserve order & dedupe

    return BuildMeta(sha=sha, short_sha=short_sha, ref=ref, time=time, source=source)


BUILD_META = get_build_meta()

def resolve_build_meta() -> BuildMeta:
    """Return the most up-to-date build metadata available.

    If the initial snapshot (captured at import time) already contains the SHA
    we can reuse it.  Otherwise we re-read the environment and persisted file –
    this helps in App Runner deployments where the env vars might appear with a
    slight delay after the process boots.
    """

    global BUILD_META  # noqa: PLW0603 – intentionally refreshing cache

    if BUILD_META.sha != "unknown":
        return BUILD_META

    refreshed = get_build_meta()
    if refreshed.sha != "unknown":
        BUILD_META = refreshed
    return BUILD_META
