"""Utilities for build metadata injected at image build time.

The GitHub Actions workflow populates ``BUILD_SHA``, ``BUILD_REF`` and
``BUILD_TIME`` as build arguments when baking the Docker image.  App Runner will
then expose them as environment variables at runtime.  Centralising the logic
for reading and shaping these values makes it easier to reuse from different
routers and to add debugging information when something goes wrong (for
instance, when ``/version`` keeps returning ``"unknown"`` during deployments).

In App Runner we noticed sporadic situations where the environment variables are
temporarily unavailable when the process starts.  To make the automation more
robust we persist the metadata to a JSON file and a tiny Python module during
the Docker build, falling back to those snapshots if needed.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from dataclasses import dataclass

try:  # pragma: no cover - extremely defensive
    from app._build_meta_snapshot import BUILD_SNAPSHOT
except Exception:  # noqa: BLE001 - best effort fallback
    BUILD_SNAPSHOT = {
        "sha": "unknown",
        "ref": "unknown",
        "time": "unknown",
        "aliases": {},
    }


ENV_VARIANTS: dict[str, tuple[str, ...]] = {
    "sha": (
        "BUILD_SHA",
        "IMAGE_BUILD_SHA",
        "APP_BUILD_SHA",
        "SOURCE_VERSION",
        "GITHUB_SHA",
        "COMMIT_SHA",
        "CI_COMMIT_SHA",
        "REVISION",
        "ORG_OPENCONTAINERS_IMAGE_REVISION",
    ),
    "ref": (
        "BUILD_REF",
        "IMAGE_BUILD_REF",
        "APP_BUILD_REF",
        "GITHUB_REF_NAME",
        "GITHUB_REF",
        "CI_COMMIT_REF_NAME",
        "SOURCE_BRANCH",
    ),
    "time": (
        "BUILD_TIME",
        "IMAGE_BUILD_TIME",
        "APP_BUILD_TIME",
        "BUILD_TIMESTAMP",
        "CI_PIPELINE_CREATED_AT",
    ),
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


def _clean(value: object | None) -> str:
    """Strip whitespace and fall back to ``"unknown"``."""

    if value is None:
        return "unknown"
    if isinstance(value, str):
        cleaned = value.strip()
    else:
        cleaned = str(value).strip()
    return cleaned if cleaned else "unknown"

def _first_known_from(candidate: object | None) -> str:
    """Return the first non-``"unknown"`` entry from a nested structure."""

    if isinstance(candidate, Mapping):
        for value in candidate.values():
            cleaned = _clean(value)
            if cleaned != "unknown":
                return cleaned
        return "unknown"

    if isinstance(candidate, (list, tuple, set)):
        for value in candidate:
            cleaned = _clean(value)
            if cleaned != "unknown":
                return cleaned
        return "unknown"

    return _clean(candidate)


def _first_known_for_field(
    aliases: Mapping[str, object],
    field: str,
    variants: tuple[str, ...],
) -> str:
    """Return the first available alias for a given metadata field."""

    for key in (field, *variants):
        value = _first_known_from(aliases.get(key))
        if value != "unknown":
            return value
    return "unknown"

def get_build_meta() -> BuildMeta:
    """Collect build metadata from environment variables.

    ``BUILD_SHA`` contains the commit that triggered the image build.  If it is
    missing we keep the ``unknown`` placeholder – useful to quickly detect that
    the pipeline did not inject the build args (the typical cause behind the
    repeated ``{"build":"unknown"}`` responses seen in App Runner health checks).
    """

    # 1) collect from environment ------------------------------------------
    source_parts: list[str] = []
    env_used: list[str] = []

    def _pull_env(field: str) -> str:
        for name in ENV_VARIANTS.get(field, ()):  # pragma: no branch - tiny tuple
            value = _clean(os.getenv(name))
            if value != "unknown":
                env_used.append(name)
                return value
        return "unknown"

    sha = _pull_env("sha")
    ref = _pull_env("ref")
    time = _pull_env("time")

    if env_used:
        source_parts.append("env")
        source_parts.extend(f"env:{name}" for name in env_used)

    # 2) fallback to persisted file ----------------------------------------
    meta_path = os.getenv("BUILD_META_FILE")
    if meta_path:
        candidate_paths = [Path(meta_path)]
    else:
        candidate_paths = [
            Path(__file__).resolve().parent.parent / ".build-meta.json",
            Path("/.build-meta.json"),
        ]

    for path in candidate_paths:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            continue
        except Exception:
            # Ignore malformed files – we just fall back to env defaults.
            continue
        if not isinstance(data, Mapping) or not data:
            continue

        source_parts.append(f"file:{path.name}")

        aliases_obj = data.get("aliases")
        aliases = aliases_obj if isinstance(aliases_obj, Mapping) else None

        if sha == "unknown":
            loaded_sha = _clean(data.get("sha"))
            if loaded_sha != "unknown":
                sha = loaded_sha
            elif aliases:
                alias_sha = _first_known_for_field(aliases, "sha", ENV_VARIANTS["sha"])
                if alias_sha != "unknown":
                    sha = alias_sha

        if ref == "unknown":
            loaded_ref = _clean(data.get("ref"))
            if loaded_ref != "unknown":
                ref = loaded_ref
            elif aliases:
                alias_ref = _first_known_for_field(aliases, "ref", ENV_VARIANTS["ref"])
                if alias_ref != "unknown":
                    ref = alias_ref

        if time == "unknown":
            loaded_time = _clean(data.get("time"))
            if loaded_time != "unknown":
                time = loaded_time
            elif aliases:
                alias_time = _first_known_for_field(aliases, "time", ENV_VARIANTS["time"])
                if alias_time != "unknown":
                    time = alias_time
        break

    # 3) fallback to baked snapshot module --------------------------------
    snapshot_used = False
    snapshot = BUILD_SNAPSHOT if isinstance(BUILD_SNAPSHOT, Mapping) else {}
    snapshot_aliases_obj = snapshot.get("aliases") if snapshot else None
    snapshot_aliases = (
        snapshot_aliases_obj if isinstance(snapshot_aliases_obj, Mapping) else None
    )

    if sha == "unknown":
        snapshot_sha = _clean(snapshot.get("sha")) if snapshot else "unknown"
        if snapshot_sha != "unknown":
            sha = snapshot_sha
            snapshot_used = True
        elif snapshot_aliases:
            alias_sha = _first_known_for_field(snapshot_aliases, "sha", ENV_VARIANTS["sha"])
            if alias_sha != "unknown":
                sha = alias_sha
                snapshot_used = True

    if ref == "unknown":
        snapshot_ref = _clean(snapshot.get("ref")) if snapshot else "unknown"
        if snapshot_ref != "unknown":
            ref = snapshot_ref
            snapshot_used = True
        elif snapshot_aliases:
            alias_ref = _first_known_for_field(snapshot_aliases, "ref", ENV_VARIANTS["ref"])
            if alias_ref != "unknown":
                ref = alias_ref
                snapshot_used = True

    if time == "unknown":
        snapshot_time = _clean(snapshot.get("time")) if snapshot else "unknown"
        if snapshot_time != "unknown":
            time = snapshot_time
            snapshot_used = True
        elif snapshot_aliases:
            alias_time = _first_known_for_field(snapshot_aliases, "time", ENV_VARIANTS["time"])
            if alias_time != "unknown":
                time = alias_time
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
