from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from domain import AIModel, SECTION_CODE_SET


class ManifestValidationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_model_manifest(model_root: Path) -> dict[str, Any]:
    root = model_root.expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ManifestValidationError("model_manifest_missing")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError("model_manifest_invalid") from exc

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 72:
        raise ManifestValidationError("model_manifest_requires_72_artifacts")

    seen: set[tuple[str, str]] = set()
    for artifact in artifacts:
        architecture = artifact.get("architecture")
        section = artifact.get("section")
        relative_path = artifact.get("path")
        expected_size = artifact.get("size_bytes")
        expected_hash = artifact.get("sha256")

        try:
            AIModel(architecture)
        except ValueError as exc:
            raise ManifestValidationError("model_manifest_architecture_invalid") from exc
        if section not in SECTION_CODE_SET:
            raise ManifestValidationError("model_manifest_section_invalid")
        if (architecture, section) in seen:
            raise ManifestValidationError("model_manifest_duplicate_artifact")
        seen.add((architecture, section))

        path = (root / str(relative_path)).resolve()
        if root not in path.parents or not path.is_file():
            raise ManifestValidationError("model_artifact_missing")
        if path.stat().st_size != expected_size:
            raise ManifestValidationError("model_artifact_size_mismatch")
        if _sha256(path) != expected_hash:
            raise ManifestValidationError("model_artifact_checksum_mismatch")

    expected = {
        (model.value, section)
        for model in AIModel
        for section in SECTION_CODE_SET
    }
    if seen != expected:
        raise ManifestValidationError("model_manifest_matrix_incomplete")
    return manifest
