"""Utilities for build metadata injected at image build time.

The GitHub Actions workflow populates ``BUILD_SHA``, ``BUILD_REF`` and
``BUILD_TIME`` as build arguments when baking the Docker image.  App Runner will
then expose them as environment variables at runtime.  Centralising the logic
for reading and shaping these values makes it easier to reuse from different
routers and to add debugging information when something goes wrong (for
instance, when ``/version`` keeps returning ``"unknown"`` during deployments).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


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

    sha = _clean(os.getenv("BUILD_SHA"))
    ref = _clean(os.getenv("BUILD_REF"))
    time = _clean(os.getenv("BUILD_TIME"))

    short_sha = sha[:7] if sha not in {"", "unknown"} else "unknown"

    source = "env"
    if sha == "unknown" and ref == "unknown" and time == "unknown":
        source = "default"

    return BuildMeta(sha=sha, short_sha=short_sha, ref=ref, time=time, source=source)


BUILD_META = get_build_meta()
