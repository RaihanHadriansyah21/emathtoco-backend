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


def _input_shape_for(architecture: str) -> list[int]:
    return [299, 299, 3] if architecture == AIModel.INCEPTION_V3.value else [224, 224, 3]


def _preprocessing_for(architecture: str) -> str:
    if architecture == AIModel.MOBILENET_V2.value:
        return "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_MOBILENETV2_PREPROCESS_INPUT"
    if architecture == AIModel.DENSENET_121.value:
        return "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_DENSENET121_PREPROCESS_INPUT"
    if architecture == AIModel.INCEPTION_V3.value:
        return "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_INCEPTIONV3_PREPROCESS_INPUT"
    return "BGR_TO_RGB_RESIZE_FLOAT32_DIVIDE_255"


def normalize_model_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize supported model manifest formats to the runtime contract.

    Supported inputs:
    - Runtime format: {"artifacts": [...]}.
    - Training export format from Models_New: {"models": {"MobileNetV2": {"sections": ...}}}.
    """
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, list):
        return manifest

    training_models = manifest.get("models")
    if not isinstance(training_models, dict):
        raise ManifestValidationError("model_manifest_requires_72_artifacts")

    normalized_artifacts: list[dict[str, Any]] = []
    for model in AIModel:
        model_entry = training_models.get(model.value)
        if not isinstance(model_entry, dict):
            continue
        sections = model_entry.get("sections")
        if not isinstance(sections, dict):
            continue

        for raw_section, section_entry in sections.items():
            if not isinstance(section_entry, dict):
                continue
            section = f"S-{str(raw_section).upper()}"
            # Runtime artifact names are fixed as model_<section>.h5. Some training
            # exports contain display names such as Section_4f.h5 for individual
            # rows, so do not trust that field for runtime path resolution.
            file_name = f"model_{str(raw_section).lower()}.h5"
            normalized_artifacts.append(
                {
                    "architecture": model.value,
                    "section": section,
                    "path": f"{model.value}/{file_name}",
                    "size_bytes": section_entry.get("file_size_bytes"),
                    "sha256": section_entry.get("sha256"),
                    "format": "keras-h5",
                    "input_shape": _input_shape_for(model.value),
                    "preprocessing": _preprocessing_for(model.value),
                    "version": str(manifest.get("ratio") or "unknown"),
                }
            )

    return {
        "schema_version": 1,
        "generated_from": "training-export",
        "artifacts": normalized_artifacts,
    }


def validate_model_manifest(model_root: Path) -> dict[str, Any]:
    root = model_root.expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ManifestValidationError("model_manifest_missing")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError("model_manifest_invalid") from exc

    manifest = normalize_model_manifest(manifest)
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
