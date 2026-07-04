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
