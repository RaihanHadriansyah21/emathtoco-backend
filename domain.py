from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    DOSEN = "dosen"
    MAHASISWA = "mahasiswa"


class AIModel(StrEnum):
    MOBILENET_V2 = "MobileNetV2"
    DENSENET_121 = "DenseNet121"
    INCEPTION_V3 = "InceptionV3"


class SubmissionStatus(StrEnum):
    DRAFT = "draft"
    REUPLOAD_REQUIRED = "reupload_required"
    SUBMITTED = "submitted"
    PROCESSING_AI = "processing_ai"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"
    FAILED = "failed"


class AIStatus(StrEnum):
    IDLE = "idle"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"


SECTION_CODES = tuple(
    f"S-{question}{part}"
    for question in range(1, 5)
    for part in ("A", "B", "C", "D", "E", "F")
)
SECTION_CODE_SET = frozenset(SECTION_CODES)
MAX_SCORE_BY_SECTION = {
    section: 5 if section.endswith("F") else 4 for section in SECTION_CODES
}
MAX_TOTAL_SCORE = 100


def get_domain_contract() -> dict[str, object]:
    return {
        "user_roles": [role.value for role in UserRole],
        "ai_models": [model.value for model in AIModel],
        "submission_statuses": [status.value for status in SubmissionStatus],
        "ai_statuses": [status.value for status in AIStatus],
        "section_codes": list(SECTION_CODES),
        "max_score_by_section": MAX_SCORE_BY_SECTION,
        "max_total_score": MAX_TOTAL_SCORE,
    }
