"""One-off, guarded Supabase Storage copy utility.

All credentials and project URLs must be supplied through environment
variables. The destination purge is blocked unless the caller confirms the
exact destination project reference.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

from supabase import Client, create_client


SOURCE_URL = os.getenv("SOURCE_SUPABASE_URL", "").rstrip("/")
SOURCE_KEY = os.getenv("SOURCE_SUPABASE_SECRET_KEY", "")
DESTINATION_URL = os.getenv("DESTINATION_SUPABASE_URL", "").rstrip("/")
DESTINATION_KEY = os.getenv("DESTINATION_SUPABASE_SECRET_KEY", "")
SOURCE_MANIFEST = Path(
    os.getenv(
        "SOURCE_STORAGE_MANIFEST",
        "C:/Users/User/AppData/Local/Temp/clean_manifest.json",
    )
)
DESTINATION_MANIFEST = Path(
    os.getenv(
        "DESTINATION_STORAGE_MANIFEST",
        "C:/Users/User/AppData/Local/Temp/clean_dest_manifest.json",
    )
)


def project_ref(url: str) -> str:
    host = url.split("://", 1)[-1].split("/", 1)[0]
    return host.split(".", 1)[0]


def validate_configuration() -> None:
    values = {
        "SOURCE_SUPABASE_URL": SOURCE_URL,
        "SOURCE_SUPABASE_SECRET_KEY": SOURCE_KEY,
        "DESTINATION_SUPABASE_URL": DESTINATION_URL,
        "DESTINATION_SUPABASE_SECRET_KEY": DESTINATION_KEY,
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
    if SOURCE_URL == DESTINATION_URL:
        raise RuntimeError("Source and destination projects must be different.")

    expected = project_ref(DESTINATION_URL)
    actual = os.getenv("CONFIRM_DESTINATION_PURGE", "")
    if actual != expected:
        raise RuntimeError(
            "Destination cleanup is blocked. Set "
            f"CONFIRM_DESTINATION_PURGE={expected} to confirm the exact project."
        )

    for manifest in (SOURCE_MANIFEST, DESTINATION_MANIFEST):
        if not manifest.is_file():
            raise FileNotFoundError(f"Storage manifest not found: {manifest}")


def load_manifest(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"Manifest must contain a JSON array: {path}")
    required = {"bucket_id", "name"}
    for index, item in enumerate(value):
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"Invalid manifest entry at index {index}: {path}")
    return value


def chunked(values: list[str], size: int = 100):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def object_label(bucket: str, path: str) -> str:
    digest = hashlib.sha256(f"{bucket}/{path}".encode()).hexdigest()[:12]
    return f"{bucket}/object-{digest}"


def purge_manifest_objects(client: Client, objects: list[dict[str, Any]]) -> None:
    by_bucket: dict[str, list[str]] = {}
    for item in objects:
        by_bucket.setdefault(str(item["bucket_id"]), []).append(str(item["name"]))

    for bucket, paths in by_bucket.items():
        for batch in chunked(paths):
            client.storage.from_(bucket).remove(batch)
        print(f"Purged {len(paths)} manifest objects from bucket {bucket}.")


def download_with_retry(
    client: Client, bucket: str, path: str, attempts: int = 3
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return client.storage.from_(bucket).download(path)
        except Exception as error:  # SDK raises provider-specific exceptions
            last_error = error
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(
        f"Download failed for {object_label(bucket, path)} after {attempts} attempts"
    ) from last_error


def upload_with_retry(
    client: Client,
    bucket: str,
    path: str,
    payload: bytes,
    content_type: str,
    attempts: int = 3,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            client.storage.from_(bucket).upload(
                path,
                payload,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return
        except Exception as error:
            last_error = error
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(
        f"Upload failed for {object_label(bucket, path)} after {attempts} attempts"
    ) from last_error


def main() -> int:
    validate_configuration()
    source_objects = load_manifest(SOURCE_MANIFEST)
    destination_objects = load_manifest(DESTINATION_MANIFEST)

    source = create_client(SOURCE_URL, SOURCE_KEY)
    destination = create_client(DESTINATION_URL, DESTINATION_KEY)

    purge_manifest_objects(destination, destination_objects)

    copied: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, item in enumerate(source_objects, start=1):
        bucket = str(item["bucket_id"])
        path = str(item["name"])
        label = object_label(bucket, path)
        try:
            payload = download_with_retry(source, bucket, path)
            expected_size = item.get("size")
            if expected_size is not None and len(payload) != int(expected_size):
                raise ValueError(
                    f"Size mismatch for {label}: expected {expected_size}, "
                    f"received {len(payload)}"
                )
            upload_with_retry(
                destination,
                bucket,
                path,
                payload,
                str(item.get("mimetype") or "application/octet-stream"),
            )
            copied.append(item)
            print(f"[{index}/{len(source_objects)}] Copied {label}.")
        except Exception as error:
            failures.append(f"{label}: {type(error).__name__}")
            print(f"[{index}/{len(source_objects)}] Failed {label}.", file=sys.stderr)

    verification_failures = 0
    for item in random.sample(copied, min(20, len(copied))):
        bucket = str(item["bucket_id"])
        path = str(item["name"])
        source_bytes = download_with_retry(source, bucket, path)
        destination_bytes = download_with_retry(destination, bucket, path)
        if hashlib.sha256(source_bytes).digest() != hashlib.sha256(
            destination_bytes
        ).digest():
            verification_failures += 1

    print(
        json.dumps(
            {
                "source_objects": len(source_objects),
                "copied": len(copied),
                "failed": len(failures),
                "sample_verification_failures": verification_failures,
                "failure_labels": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures and verification_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
