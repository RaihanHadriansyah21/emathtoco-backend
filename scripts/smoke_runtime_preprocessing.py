from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from services.model_loader import load_mobilenet_model
from services.model_manifest import normalize_model_manifest
from services.preprocess import preprocess_image


def _synthetic_section() -> np.ndarray:
    """Create a camera-like white answer section with dark handwriting."""
    image = np.full((900, 1400, 3), 244, dtype=np.uint8)
    cv2.rectangle(image, (12, 12), (1387, 887), (25, 25, 25), 6)
    cv2.putText(
        image,
        "4. b   MSE = 0.5",
        (90, 250),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.2,
        (18, 18, 18),
        6,
        cv2.LINE_AA,
    )
    cv2.line(image, (95, 330), (780, 330), (30, 30, 30), 5)
    return image


def run(model_root: Path, architecture: str, section: str) -> dict[str, object]:
    manifest_path = model_root / "manifest.json"
    manifest = normalize_model_manifest(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    artifact = next(
        (
            entry
            for entry in manifest["artifacts"]
            if entry["architecture"] == architecture and entry["section"] == section
        ),
        None,
    )
    if artifact is None:
        raise RuntimeError(f"model_artifact_not_found:{architecture}:{section}")

    height, width, channels = artifact["input_shape"]
    if channels != 3:
        raise RuntimeError("model_input_channels_must_be_three")
    model_input = preprocess_image(
        _synthetic_section(),
        (width, height),
        artifact["preprocessing"],
    )
    if model_input.shape != (1, height, width, channels):
        raise RuntimeError(f"invalid_preprocessed_shape:{model_input.shape}")
    if model_input.dtype != np.float32 or not np.isfinite(model_input).all():
        raise RuntimeError("invalid_preprocessed_values")

    model_path = model_root / artifact["path"]
    model = load_mobilenet_model(model_path)
    output = np.asarray(model.predict(model_input, verbose=0))
    if output.ndim != 2 or output.shape[0] != 1 or not np.isfinite(output).all():
        raise RuntimeError(f"invalid_model_output:{artifact['path']}")

    return {
        "architecture": architecture,
        "section": section,
        "artifact": artifact["path"],
        "preprocessing": artifact["preprocessing"],
        "input_shape": list(model_input.shape),
        "input_min": round(float(model_input.min()), 6),
        "input_max": round(float(model_input.max()), 6),
        "output_shape": list(output.shape),
        "predicted_class": int(np.argmax(output[0])),
        "confidence": round(float(np.max(output[0])), 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--section", required=True)
    args = parser.parse_args()
    result = run(
        args.model_root.expanduser().resolve(),
        args.architecture,
        args.section,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
