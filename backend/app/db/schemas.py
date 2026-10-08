from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)


class UserRead(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StudyCreate(BaseModel):
    name: str
    owner_user_id: Optional[int] = None
    sequences_present: Dict[str, bool] = Field(default_factory=dict)
    qc_flags: Dict[str, Any] = Field(default_factory=dict)


class StudyRead(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    sequences_present: Dict[str, bool]
    qc_flags: Dict[str, Any]
    created_at: datetime
    owner_user_id: Optional[int] = None

    model_config = {"from_attributes": True}


class FileArtifactRead(BaseModel):
    id: int
    kind: str
    path: str
    size_bytes: int
    checksum: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricRead(BaseModel):
    wt_ml: float
    tc_ml: float
    et_ml: float
    edema_core_ratio: float
    confidence_summary: float
    low_confidence_fraction: float
    model_agreement_wt_dice: Optional[float] = None
    label_disagreement_ml: Optional[float] = None
    runtime_sec: float
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ComparisonCreate(BaseModel):
    study_a_id: uuid.UUID
    study_b_id: uuid.UUID


class ComparisonRead(BaseModel):
    id: int
    study_a_id: uuid.UUID
    study_b_id: uuid.UUID
    volume_a_ml: float
    volume_b_ml: float
    pct_change: float
    rano_label: str
    created_at: datetime

    model_config = {"from_attributes": True}
