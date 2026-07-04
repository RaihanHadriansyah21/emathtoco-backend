from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a student-grouped split from a real dataset manifest.",
    )
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    return parser.parse_args()


def stable_bucket(student_id: str) -> int:
    digest = hashlib.sha256(student_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % 10_000


def main() -> int:
    args = parse_args()
    try:
        if not 0.05 <= args.test_ratio <= 0.5:
            raise ValueError("test_ratio_out_of_range")
        if not args.dataset_manifest.is_file():
            raise ValueError("dataset_manifest_missing")

        records = json.loads(args.dataset_manifest.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ValueError("dataset_manifest_must_be_non_empty_array")

        required = {"student_id", "image_path", "section_code", "score"}
        for index, record in enumerate(records):
            if not isinstance(record, dict) or not required.issubset(record):
                raise ValueError(f"dataset_record_invalid:{index}")
            if not Path(record["image_path"]).expanduser().is_file():
                raise ValueError(f"original_image_missing:{index}")

        threshold = int(args.test_ratio * 10_000)
        train = [
            record
            for record in records
            if stable_bucket(str(record["student_id"])) >= threshold
        ]
        test = [
            record
            for record in records
            if stable_bucket(str(record["student_id"])) < threshold
        ]
        if not train or not test:
            raise ValueError("split_produced_empty_partition")

        train_students = {str(record["student_id"]) for record in train}
        test_students = {str(record["student_id"]) for record in test}
        overlap = sorted(train_students & test_students)
        if overlap:
            raise ValueError("student_overlap_detected")

        args.output_directory.mkdir(parents=True, exist_ok=True)
        (args.output_directory / "train.json").write_text(
            json.dumps(train, indent=2) + "\n",
            encoding="utf-8",
        )
        (args.output_directory / "test.json").write_text(
            json.dumps(test, indent=2) + "\n",
            encoding="utf-8",
        )
        (args.output_directory / "split-report.json").write_text(
            json.dumps(
                {
                    "source": str(args.dataset_manifest.resolve()),
                    "train_records": len(train),
                    "test_records": len(test),
                    "train_students": len(train_students),
                    "test_students": len(test_students),
                    "student_overlap_count": 0,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        print(f"Split validation aborted: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
