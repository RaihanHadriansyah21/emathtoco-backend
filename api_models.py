from __future__ import annotations

import json
from typing import Any, Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, field_validator

from domain import AIModel, SECTION_CODE_SET, UserRole


class BatchPredictionRequest(BaseModel):
    submission_ids: list[UUID] = Field(min_length=1, max_length=25)
    model: AIModel | None = None

    @field_validator("submission_ids")
    @classmethod
    def unique_submission_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


class PredictionAcceptedResponse(BaseModel):
    job_id: str
    status: Literal["queued"]
    accepted_ids: list[UUID]
    rejected: dict[str, str]


class AuditEventRequest(BaseModel):
    action: str = Field(pattern=r"^[A-Z0-9_]{1,64}$")
    target: str = Field(pattern=r"^[a-z_]{1,64}$")
    target_id: str | None = Field(default=None, max_length=128)
    detail: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("detail", "details"),
    )

    @field_validator("detail")
    @classmethod
    def validate_detail_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(value, separators=(",", ":"), default=str)
        if len(encoded.encode("utf-8")) > 8192:
            raise ValueError("audit detail exceeds 8192 bytes")
        return value


class PredictionIdsRequest(BaseModel):
    lembar_jawaban_ids: list[UUID] = Field(min_length=1, max_length=500)


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, str | bool | dict[str, Any]]

    @field_validator("settings")
    @classmethod
    def validate_settings(
        cls,
        value: dict[str, str | bool | dict[str, Any]],
    ) -> dict[str, str | bool | dict[str, Any]]:
        allowed = {
            "active_model",
            "auto_run_ai",
            "verbose_logging",
            "future_flags",
        }
        if not value or set(value) - allowed:
            raise ValueError("unsupported system setting")
        if "active_model" in value:
            AIModel(str(value["active_model"]))
        encoded = json.dumps(value, separators=(",", ":"), default=str)
        if len(encoded.encode("utf-8")) > 8192:
            raise ValueError("settings payload exceeds 8192 bytes")
        return value


class DemoResetRequest(BaseModel):
    reset_type: Literal["submissions", "enrollments", "all"]


class UserRoleUpdateRequest(BaseModel):
    new_role: UserRole


class ReviewScore(BaseModel):
    section_code: str
    nilai_dosen: float | None = Field(default=None, ge=0, le=5)
    nilai_final: float | None = Field(default=None, ge=0, le=5)
    feedback: str | None = Field(default=None, max_length=2000)

    @field_validator("section_code")
    @classmethod
    def valid_section(cls, value: str) -> str:
        if value not in SECTION_CODE_SET:
            raise ValueError("invalid section code")
        return value


class ReviewRequest(BaseModel):
    model: AIModel
    scores: list[ReviewScore] = Field(min_length=24, max_length=24)

    @field_validator("scores")
    @classmethod
    def all_sections_once(cls, value: list[ReviewScore]) -> list[ReviewScore]:
        sections = {score.section_code for score in value}
        if sections != SECTION_CODE_SET:
            raise ValueError("all 24 sections are required exactly once")
        return value


class ReuploadRequest(BaseModel):
    section_code: str
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("section_code")
    @classmethod
    def valid_section(cls, value: str) -> str:
        if value not in SECTION_CODE_SET:
            raise ValueError("invalid section code")
        return value
