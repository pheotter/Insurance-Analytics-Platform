"""HTTP request schemas; domain rules remain in the service layer."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from actuarial_workflow.domain import SelectionSource


class CreateSelectionVersionRequest(BaseModel):
    model_run_id: str = Field(min_length=1)
    comment: str | None = None


class ReviewActionRequest(BaseModel):
    comment: str | None = None


class RejectRequest(BaseModel):
    comment: str = Field(min_length=1)


class LdfSelectionPayload(BaseModel):
    triangle_grain: str
    development_pool_id: str
    pool_level: str
    line_of_business: str
    measure_type: str
    from_age_months: int = Field(ge=0)
    to_age_months: int = Field(gt=0)
    selected_method: str
    selected_ldf: float = Field(gt=0)
    selection_source: SelectionSource = SelectionSource.CANDIDATE
    selection_reason: str | None = None


class TailSelectionPayload(BaseModel):
    triangle_grain: str
    development_pool_id: str
    pool_level: str
    line_of_business: str
    measure_type: str
    development_method: str
    selected_tail_method: str
    selected_tail_factor: float = Field(ge=1)
    selection_source: SelectionSource = SelectionSource.CANDIDATE
    selection_reason: str | None = None


class UltimateSelectionPayload(BaseModel):
    triangle_grain: str
    development_pool_id: str
    pool_level: str
    line_of_business: str
    measure_type: str
    accident_period: date
    development_method: str
    tail_method: str
    selected_ultimate_method: str
    selected_ultimate_value: float = Field(ge=0)
    selection_source: SelectionSource = SelectionSource.CANDIDATE
    selection_reason: str | None = None


class ReplaceLdfSelectionsRequest(BaseModel):
    selections: list[LdfSelectionPayload] = Field(min_length=1)


class ReplaceTailSelectionsRequest(BaseModel):
    selections: list[TailSelectionPayload] = Field(min_length=1)


class ReplaceUltimateSelectionsRequest(BaseModel):
    selections: list[UltimateSelectionPayload] = Field(min_length=1)
