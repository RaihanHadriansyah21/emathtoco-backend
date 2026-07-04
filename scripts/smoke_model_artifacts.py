from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from services.model_loader import load_mobilenet_model
from services.model_manifest import validate_model_manifest
from services.preprocess import preprocess_image


def deterministic_input(height: int, width: int, channels: int) -> np.ndarray:
    values = np.linspace(
        0.0,
        1.0,
        num=height * width * channels,
        dtype=np.float32,
    )
    return values.reshape((1, height, width, channels))


def validate_preprocessing_contract() -> None:
    bgr_pixel = np.array([[[10, 20, 30]]], dtype=np.uint8)
    actual = preprocess_image(bgr_pixel, (1, 1))
    expected = np.array([[[[30, 20, 10]]]], dtype=np.float32) / 255.0
    if (
        actual.dtype != np.float32
        or actual.shape != (1, 1, 1, 3)
        or not np.allclose(actual, expected)
    ):
        raise RuntimeError("preprocessing_contract_mismatch")


def run_smoke(
    model_root: Path,
    architecture: str | None = None,
    section: str | None = None,
) -> dict[str, dict[str, int | float]]:
    if architecture and section:
        manifest = json.loads(
            (model_root / "manifest.json").read_text(encoding="utf-8"),
        )
    else:
        manifest = validate_model_manifest(model_root)
    results: dict[str, dict[str, int | float]] = {}

    for artifact in manifest["artifacts"]:
        if architecture and artifact["architecture"] != architecture:
            continue
        if section and artifact["section"] != section:
            continue
        artifact_path = model_root / artifact["path"]
        if (
            not artifact_path.is_file()
            or artifact_path.stat().st_size != artifact["size_bytes"]
        ):
            raise RuntimeError(f"invalid_model_artifact:{artifact['path']}")
        input_shape = artifact["input_shape"]
        sample = deterministic_input(*input_shape)
        model = load_mobilenet_model(artifact_path)
        output = np.asarray(model.predict(sample, verbose=0))
        if output.ndim != 2 or output.shape[0] != 1 or not np.isfinite(output).all():
            raise RuntimeError(f"invalid_model_output:{artifact['path']}")

        key = f"{artifact['architecture']}:{artifact['section']}"
        results[key] = {
            "argmax": int(np.argmax(output[0])),
            "confidence": round(float(np.max(output[0])), 6),
            "output_size": int(output.shape[1]),
        }
        del model, output, sample
        tf.keras.backend.clear_session()
        gc.collect()

    return results


def compare_golden(
    actual: dict[str, dict[str, int | float]],
    expected: dict[str, dict[str, int | float]],
) -> None:
    if actual.keys() != expected.keys():
        raise RuntimeError("golden_model_matrix_mismatch")
    for key, actual_result in actual.items():
        expected_result = expected[key]
        if actual_result["argmax"] != expected_result["argmax"]:
            raise RuntimeError(f"golden_class_mismatch:{key}")
        if actual_result["output_size"] != expected_result["output_size"]:
            raise RuntimeError(f"golden_output_shape_mismatch:{key}")
        confidence_delta = abs(
            float(actual_result["confidence"])
            - float(expected_result["confidence"])
        )
        if confidence_delta > 0.0001:
            raise RuntimeError(f"golden_confidence_mismatch:{key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--write-golden", action="store_true")
    parser.add_argument("--architecture")
    parser.add_argument("--section")
    args = parser.parse_args()

    model_root = args.model_root.expanduser().resolve()
    golden_path = args.golden.expanduser().resolve()
    validate_preprocessing_contract()
    if bool(args.architecture) != bool(args.section):
        raise RuntimeError("architecture_and_section_must_be_used_together")
    actual = run_smoke(model_root, args.architecture, args.section)
    if args.architecture and len(actual) != 1:
        raise RuntimeError("single_model_not_found")

    if args.write_golden:
        existing_artifacts: dict[str, dict[str, int | float]] = {}
        if golden_path.is_file():
            existing = json.loads(golden_path.read_text(encoding="utf-8"))
            existing_artifacts = existing.get("artifacts", {})
        existing_artifacts.update(actual)
        golden_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tensorflow_version": tf.__version__,
                    "input": "deterministic_rgb_gradient_float32_0_1",
                    "artifacts": existing_artifacts,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0

    expected_document = json.loads(golden_path.read_text(encoding="utf-8"))
    expected_artifacts = expected_document["artifacts"]
    if args.architecture:
        key = next(iter(actual))
        expected_artifacts = {key: expected_artifacts[key]}
    compare_golden(actual, expected_artifacts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
