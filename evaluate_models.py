from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate real E-MATHTOCO images. No synthetic fallback exists.",
    )
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument(
        "--architecture",
        choices=("MobileNetV2", "DenseNet121", "InceptionV3"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_dataset(path: Path) -> list[dict]:
    if not path.is_file():
        raise ValueError("dataset_manifest_missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("dataset_manifest_must_be_non_empty_array")

    required = {"image_path", "section_code", "gold_score"}
    for index, record in enumerate(data):
        if not isinstance(record, dict) or not required.issubset(record):
            raise ValueError(f"dataset_record_invalid:{index}")
        image_path = Path(record["image_path"]).expanduser().resolve()
        if not image_path.is_file():
            raise ValueError(f"original_image_missing:{index}")
        record["image_path"] = str(image_path)
    return data


def classification_metrics(
    gold: list[int],
    predicted: list[int],
) -> tuple[float, float, float]:
    if len(gold) != len(predicted) or not gold:
        raise ValueError("metric_inputs_invalid")
    labels = sorted(set(gold) | set(predicted))
    accuracy = sum(a == b for a, b in zip(gold, predicted, strict=True)) / len(gold)

    f1_scores: list[float] = []
    for label in labels:
        true_positive = sum(
            a == label and b == label
            for a, b in zip(gold, predicted, strict=True)
        )
        false_positive = sum(
            a != label and b == label
            for a, b in zip(gold, predicted, strict=True)
        )
        false_negative = sum(
            a == label and b != label
            for a, b in zip(gold, predicted, strict=True)
        )
        precision = true_positive / (true_positive + false_positive) if (
            true_positive + false_positive
        ) else 0.0
        recall = true_positive / (true_positive + false_negative) if (
            true_positive + false_negative
        ) else 0.0
        f1_scores.append(
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

    observed = accuracy
    expected = 0.0
    for label in labels:
        gold_rate = sum(value == label for value in gold) / len(gold)
        predicted_rate = sum(value == label for value in predicted) / len(predicted)
        expected += gold_rate * predicted_rate
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return accuracy, sum(f1_scores) / len(f1_scores), kappa


def main() -> int:
    args = parse_args()
    try:
        dataset = load_dataset(args.dataset_manifest)
        os.environ["MODEL_ROOT"] = str(args.model_root.expanduser().resolve())

        from services.class_mapping import get_score
        from services.model_manifest import validate_model_manifest
        from services.model_registry import MODEL_CONFIG, get_model
        from services.preprocess import preprocess_image

        import cv2
        import numpy as np

        expected_manifest = args.model_root.expanduser().resolve() / "manifest.json"
        if args.model_manifest.expanduser().resolve() != expected_manifest:
            raise ValueError("model_manifest_must_be_inside_model_root")
        validate_model_manifest(args.model_root)

        gold_scores: list[int] = []
        predicted_scores: list[int] = []
        for index, record in enumerate(dataset):
            section = str(record["section_code"])
            image = cv2.imread(record["image_path"], cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"original_image_decode_failed:{index}")
            processed = preprocess_image(
                image,
                MODEL_CONFIG[args.architecture]["input_size"],
                MODEL_CONFIG[args.architecture].get(
                    "preprocessing",
                    "BGR_TO_RGB_RESIZE_FLOAT32_DIVIDE_255",
                ),
            )
            model = get_model(section, args.architecture)
            output = model.predict(processed, verbose=0)
            predicted_class = int(np.argmax(output[0]))
            gold_scores.append(int(record["gold_score"]))
            predicted_scores.append(get_score(section, predicted_class))

        accuracy, macro_f1, kappa = classification_metrics(
            gold_scores,
            predicted_scores,
        )
        result = {
            "source": "real_dataset_manifest",
            "dataset_manifest": str(args.dataset_manifest.resolve()),
            "model_manifest": str(args.model_manifest.resolve()),
            "architecture": args.architecture,
            "sample_count": len(dataset),
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "cohens_kappa": kappa,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        print(f"Evaluation aborted: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
