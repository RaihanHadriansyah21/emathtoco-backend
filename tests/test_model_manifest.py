import hashlib
import json
from pathlib import Path

from domain import AIModel, SECTION_CODES
from services.model_manifest import validate_model_manifest


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
