from uuid import UUID

import pytest
from pydantic import ValidationError

from api_models import (
    AuditEventRequest,
    BatchPredictionRequest,
    ReviewRequest,
    UserRoleUpdateRequest,
)


def test_batch_request_deduplicates_ids() -> None:
    submission_id = UUID("10000000-0000-0000-0000-000000000001")
    request = BatchPredictionRequest(
        submission_ids=[submission_id, submission_id],
        model="MobileNetV2",
    )
    assert request.submission_ids == [submission_id]


def test_review_requires_all_sections() -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(
            model="MobileNetV2",
            scores=[
                {
                    "section_code": "S-1A",
                    "nilai_final": 4,
                }
            ]
            * 24,
        )


def test_admin_role_update_accepts_only_domain_roles() -> None:
    assert UserRoleUpdateRequest(new_role="dosen").new_role.value == "dosen"
    with pytest.raises(ValidationError):
        UserRoleUpdateRequest(new_role="superadmin")


def test_audit_detail_rejects_oversized_payload() -> None:
    with pytest.raises(ValidationError):
        AuditEventRequest(
            action="ADMIN_LOGIN",
            target="profil_pengguna",
            detail={"value": "x" * 9000},
        )
