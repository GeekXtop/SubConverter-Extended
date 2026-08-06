#!/usr/bin/env python3
"""Verify that an OCI image index has exactly one runnable amd64 image."""

from __future__ import annotations

import json
from pathlib import Path
import sys


EXPECTED_PLATFORM = "linux/amd64"
ATTESTATION_TYPE = "attestation-manifest"


def platform_name(descriptor: dict[str, object]) -> str:
    platform = descriptor.get("platform")
    if not isinstance(platform, dict):
        return "unknown/unknown"

    operating_system = str(platform.get("os", "unknown"))
    architecture = str(platform.get("architecture", "unknown"))
    variant = str(platform.get("variant", "")).strip()
    name = f"{operating_system}/{architecture}"
    return f"{name}/{variant}" if variant else name


def verify(document: object) -> tuple[list[str], int]:
    if not isinstance(document, dict):
        raise ValueError("manifest root must be a JSON object")

    manifests = document.get("manifests")
    if not isinstance(manifests, list) or not manifests:
        raise ValueError("manifest must be a non-empty OCI image index")

    runnable_platforms: list[str] = []
    attestation_count = 0
    for descriptor in manifests:
        if not isinstance(descriptor, dict):
            raise ValueError("manifest descriptor must be a JSON object")

        platform = platform_name(descriptor)
        annotations = descriptor.get("annotations")
        reference_type = (
            annotations.get("vnd.docker.reference.type")
            if isinstance(annotations, dict)
            else None
        )
        if platform == "unknown/unknown" and reference_type == ATTESTATION_TYPE:
            attestation_count += 1
            continue
        runnable_platforms.append(platform)

    if runnable_platforms != [EXPECTED_PLATFORM]:
        rendered = ", ".join(runnable_platforms) or "none"
        raise ValueError(
            f"expected only runnable platform {EXPECTED_PLATFORM}, got {rendered}"
        )

    return runnable_platforms, attestation_count


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} MANIFEST_JSON", file=sys.stderr)
        return 2

    try:
        document = json.loads(Path(sys.argv[1]).read_text())
        platforms, attestations = verify(document)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"AMD64 manifest verification failed: {error}", file=sys.stderr)
        return 1

    print(
        "Verified runnable platforms: "
        f"{', '.join(platforms)} (attestations: {attestations})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
