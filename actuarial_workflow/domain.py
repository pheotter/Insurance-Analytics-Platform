"""Domain objects shared by service, API, and persistence adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class SelectionStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SelectionSource(str, Enum):
    CANDIDATE = "CANDIDATE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class CandidateType(str, Enum):
    LDF = "ldf"
    TAIL = "tail"
    ULTIMATE = "ultimate"


@dataclass(frozen=True)
class SelectionVersion:
    selection_version_id: str
    model_run_id: str
    as_of_date: date
    status: SelectionStatus
    created_by: str
    created_at: datetime
    comment: str | None = None
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    review_comment: str | None = None
    row_version: int = 1


@dataclass(frozen=True)
class LdfSelection:
    triangle_grain: str
    development_pool_id: str
    pool_level: str
    line_of_business: str
    measure_type: str
    from_age_months: int
    to_age_months: int
    selected_method: str
    selected_ldf: float
    selection_source: SelectionSource = SelectionSource.CANDIDATE
    selection_reason: str | None = None


@dataclass(frozen=True)
class TailSelection:
    triangle_grain: str
    development_pool_id: str
    pool_level: str
    line_of_business: str
    measure_type: str
    development_method: str
    selected_tail_method: str
    selected_tail_factor: float
    selection_source: SelectionSource = SelectionSource.CANDIDATE
    selection_reason: str | None = None


@dataclass(frozen=True)
class UltimateSelection:
    triangle_grain: str
    development_pool_id: str
    pool_level: str
    line_of_business: str
    measure_type: str
    accident_period: date
    development_method: str
    tail_method: str
    selected_ultimate_method: str
    selected_ultimate_value: float
    selection_source: SelectionSource = SelectionSource.CANDIDATE
    selection_reason: str | None = None
