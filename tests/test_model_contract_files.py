import json
from pathlib import Path

from domain import AIModel, SECTION_CODE_SET


def test_manifest_and_golden_cover_same_72_artifacts() -> None:
    root = Path(__file__).resolve().parents[1] / "Models"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    golden = json.loads(
        (root / "golden_inference.json").read_text(encoding="utf-8"),
    )

    manifest_keys = {
        f"{artifact['architecture']}:{artifact['section']}"
        for artifact in manifest["artifacts"]
    }
    expected_keys = {
        f"{model.value}:{section}"
        for model in AIModel
        for section in SECTION_CODE_SET
    }

    assert len(manifest["artifacts"]) == 72
    assert manifest_keys == expected_keys
    assert set(golden["artifacts"]) == expected_keys
    assert golden["tensorflow_version"] == "2.21.0"


def test_active_models_new_manifest_matches_training_golden() -> None:
    root = Path(__file__).resolve().parents[1] / "Models_New"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    golden = json.loads(
        (root / "golden_inference.json").read_text(encoding="utf-8"),
    )

    artifacts = {
        (artifact["architecture"], artifact["section"]): artifact
        for artifact in manifest["artifacts"]
    }
    expected_keys = {
        (model.value, section)
        for model in AIModel
        for section in SECTION_CODE_SET
    }

    assert manifest["schema_version"] == 2
    assert manifest["model_collection"] == "Models_New"
    assert manifest["total_artifacts"] == 72
    assert set(artifacts) == expected_keys

    for architecture, section in expected_keys:
        raw_section = section.removeprefix("S-").lower()
        golden_entry = golden["models"][architecture]["sections"][raw_section]
        artifact = artifacts[(architecture, section)]

        assert artifact["sha256"] == golden_entry["model_sha256"]
        assert artifact["class_labels"] == golden_entry["section_class_labels"]
        assert artifact["input_shape"] == golden_entry["input_shape"][1:]
        assert artifact["output_shape"] == golden_entry["output_shape"]
        assert golden_entry["status"] == "success"
