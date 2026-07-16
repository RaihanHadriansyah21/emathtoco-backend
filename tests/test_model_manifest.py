import hashlib
import json
from pathlib import Path

from domain import AIModel, SECTION_CODES
from services.model_manifest import normalize_model_manifest, validate_model_manifest


def test_model_manifest_matrix(tmp_path: Path) -> None:
    artifacts = []
    content = b"test-model"
    digest = hashlib.sha256(content).hexdigest()
    for model in AIModel:
        for section in SECTION_CODES:
            relative = Path(model.value) / f"{section}.h5"
            model_path = tmp_path / relative
            model_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_bytes(content)
            artifacts.append(
                {
                    "architecture": model.value,
                    "section": section,
                    "path": relative.as_posix(),
                    "size_bytes": len(content),
                    "sha256": digest,
                }
            )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"artifacts": artifacts}),
        encoding="utf-8",
    )

    manifest = validate_model_manifest(tmp_path)
    assert len(manifest["artifacts"]) == 72


def test_training_export_manifest_is_normalized() -> None:
    manifest = {
        "ratio": "80:20",
        "models": {
            model.value: {
                "sections": {
                    section[2:].lower(): {
                        "file_size_bytes": 1,
                        "sha256": "x",
                    }
                    for section in SECTION_CODES
                }
            }
            for model in AIModel
        },
    }

    normalized = normalize_model_manifest(manifest)
    artifacts = normalized["artifacts"]
    by_key = {
        (artifact["architecture"], artifact["section"]): artifact
        for artifact in artifacts
    }

    assert len(artifacts) == 72
    assert by_key[("MobileNetV2", "S-1A")]["path"] == "MobileNetV2/model_1a.h5"
    assert by_key[("MobileNetV2", "S-1A")]["input_shape"] == [224, 224, 3]
    assert (
        by_key[("MobileNetV2", "S-1A")]["preprocessing"]
        == "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_MOBILENETV2_PREPROCESS_INPUT"
    )
    assert by_key[("DenseNet121", "S-1A")]["input_shape"] == [224, 224, 3]
    assert (
        by_key[("DenseNet121", "S-1A")]["preprocessing"]
        == "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_DENSENET121_PREPROCESS_INPUT"
    )
    assert by_key[("InceptionV3", "S-1A")]["input_shape"] == [299, 299, 3]
    assert (
        by_key[("InceptionV3", "S-1A")]["preprocessing"]
        == "SECTION_BINARY_NON_INVERTED_NEAREST_THEN_KERAS_INCEPTIONV3_PREPROCESS_INPUT"
    )
