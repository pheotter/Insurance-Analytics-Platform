"""Application services for governed actuarial selection workflows."""

from __future__ import annotations

import math
from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any, Iterable, TypeVar
from uuid import uuid4

from .airflow_client import AirflowClient
from .domain import (
    CandidateType,
    LdfSelection,
    SelectionSource,
    SelectionStatus,
    SelectionVersion,
    TailSelection,
    UltimateSelection,
)
from .errors import (
    InvalidTransitionError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from .repository import WorkflowRepository


SelectionRecord = LdfSelection | TailSelection | UltimateSelection
T = TypeVar("T", bound=SelectionRecord)


class SelectionService:
    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def list_model_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list_model_runs(limit=limit)

    def list_candidates(
        self,
        candidate_type: CandidateType,
        model_run_id: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = 10_000,
    ) -> list[dict[str, Any]]:
        return self.repository.list_candidates(
            candidate_type,
            model_run_id,
            filters=filters,
            limit=limit,
        )

    def create_version(
        self,
        *,
        model_run_id: str,
        actor: str,
        comment: str | None = None,
    ) -> SelectionVersion:
        actor = _required_text(actor, "actor")
        runs = self.repository.list_model_runs(limit=10_000)
        model_run = next(
            (row for row in runs if str(row["model_run_id"]) == model_run_id),
            None,
        )
        if model_run is None:
            raise WorkflowNotFoundError(f"Model run {model_run_id!r} was not found")

        version = SelectionVersion(
            selection_version_id=str(uuid4()),
            model_run_id=model_run_id,
            as_of_date=_as_date(model_run["as_of_date"]),
            status=SelectionStatus.DRAFT,
            created_by=actor,
            created_at=datetime.now(timezone.utc),
            comment=_optional_text(comment),
        )
        return self.repository.create_version(version, actor=actor)

    def get_version(self, selection_version_id: str) -> SelectionVersion:
        version = self.repository.get_version(selection_version_id)
        if version is None:
            raise WorkflowNotFoundError(
                f"Selection version {selection_version_id!r} was not found"
            )
        return version

    def list_versions(
        self,
        *,
        status: SelectionStatus | None = None,
        limit: int = 100,
    ) -> list[SelectionVersion]:
        return self.repository.list_versions(status=status, limit=limit)

    def get_selections(
        self,
        selection_version_id: str,
    ) -> dict[str, list[dict[str, Any]]]:
        self.get_version(selection_version_id)
        return self.repository.get_selections(selection_version_id)

    def replace_ldf_selections(
        self,
        selection_version_id: str,
        selections: list[LdfSelection],
        *,
        actor: str,
    ) -> None:
        self._replace(
            CandidateType.LDF, selection_version_id, selections, actor=actor
        )

    def replace_tail_selections(
        self,
        selection_version_id: str,
        selections: list[TailSelection],
        *,
        actor: str,
    ) -> None:
        self._replace(
            CandidateType.TAIL, selection_version_id, selections, actor=actor
        )

    def replace_ultimate_selections(
        self,
        selection_version_id: str,
        selections: list[UltimateSelection],
        *,
        actor: str,
    ) -> None:
        self._replace(
            CandidateType.ULTIMATE,
            selection_version_id,
            selections,
            actor=actor,
        )

    def submit(
        self,
        selection_version_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> SelectionVersion:
        version = self.get_version(selection_version_id)
        self._require_status(version, SelectionStatus.DRAFT)
        selections = self.repository.get_selections(selection_version_id)
        for name in ("ldf", "tail", "ultimate"):
            if not selections[name]:
                raise WorkflowValidationError(
                    f"At least one {name} selection is required before submission"
                )
        self._validate_cross_stage_consistency(selections)
        return self.repository.transition_version(
            selection_version_id,
            expected_status=SelectionStatus.DRAFT,
            target_status=SelectionStatus.SUBMITTED,
            actor=_required_text(actor, "actor"),
            comment=_optional_text(comment),
        )

    def _replace(
        self,
        candidate_type: CandidateType,
        selection_version_id: str,
        selections: list[T],
        *,
        actor: str,
    ) -> None:
        version = self.get_version(selection_version_id)
        self._require_status(version, SelectionStatus.DRAFT)
        if not selections:
            raise WorkflowValidationError("Selection list cannot be empty")
        self._validate_records(candidate_type, version, selections)
        records = [_selection_dict(item) for item in selections]
        self.repository.replace_selections(
            candidate_type,
            selection_version_id,
            records,
            actor=_required_text(actor, "actor"),
        )

    def _validate_records(
        self,
        candidate_type: CandidateType,
        version: SelectionVersion,
        selections: list[T],
    ) -> None:
        candidates = self.repository.list_candidates(
            candidate_type,
            version.model_run_id,
            limit=100_000,
        )
        available = [
            row
            for row in candidates
            if row.get("status") in {"AVAILABLE", "AVAILABLE_WITH_WARNING"}
        ]
        seen: set[tuple[Any, ...]] = set()
        for selection in selections:
            key = _selection_uniqueness_key(candidate_type, selection)
            if key in seen:
                raise WorkflowValidationError(
                    f"Duplicate {candidate_type.value} selection for key {key}"
                )
            seen.add(key)
            _validate_selected_value(candidate_type, selection)
            if selection.selection_source == SelectionSource.MANUAL_OVERRIDE:
                if not _optional_text(selection.selection_reason):
                    raise WorkflowValidationError(
                        "Manual overrides require a selection_reason"
                    )
                continue
            if not any(
                _candidate_matches(candidate_type, selection, candidate)
                for candidate in available
            ):
                raise WorkflowValidationError(
                    f"Selected {candidate_type.value} does not match an available "
                    f"candidate from model run {version.model_run_id}"
                )

    @staticmethod
    def _require_status(
        version: SelectionVersion,
        required: SelectionStatus,
    ) -> None:
        if version.status != required:
            raise InvalidTransitionError(
                f"Selection version is {version.status.value}; expected {required.value}"
            )

    @staticmethod
    def _validate_cross_stage_consistency(
        selections: dict[str, list[dict[str, Any]]],
    ) -> None:
        ldf_methods: dict[tuple[Any, ...], set[str]] = {}
        for row in selections["ldf"]:
            key = _scope_key(row)
            ldf_methods.setdefault(key, set()).add(str(row["selected_method"]))
        mixed = [key for key, methods in ldf_methods.items() if len(methods) != 1]
        if mixed:
            raise WorkflowValidationError(
                "MVP requires one development method across all ages for each pool/measure"
            )

        tails = {_scope_key(row): row for row in selections["tail"]}
        for key, row in tails.items():
            if key not in ldf_methods:
                raise WorkflowValidationError(f"Tail selection has no LDF selection: {key}")
            selected_method = next(iter(ldf_methods[key]))
            if row["development_method"] != selected_method:
                raise WorkflowValidationError(
                    f"Tail development method does not match selected LDF method: {key}"
                )

        measures = {str(row["measure_type"]) for row in selections["ultimate"]}
        loss_measures = {"incurred", "paid", "paid_and_expense"}
        if "reported_count" not in measures or not (measures & loss_measures):
            raise WorkflowValidationError(
                "Frequency/severity requires ultimate selections for reported_count "
                "and at least one loss measure"
            )
        for row in selections["ultimate"]:
            key = _scope_key(row)
            tail = tails.get(key)
            if tail is None:
                raise WorkflowValidationError(
                    f"Ultimate selection has no tail selection: {key}"
                )
            if (
                row["development_method"] != tail["development_method"]
                or row["tail_method"] != tail["selected_tail_method"]
            ):
                raise WorkflowValidationError(
                    f"Ultimate pattern does not match selected development/tail: {key}"
                )


class ApprovalService:
    def __init__(
        self,
        repository: WorkflowRepository,
        airflow_client: AirflowClient,
    ) -> None:
        self.repository = repository
        self.airflow_client = airflow_client

    def approve(
        self,
        selection_version_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        actor = _required_text(actor, "actor")
        version = self._get_version(selection_version_id)
        if version.status != SelectionStatus.SUBMITTED:
            raise InvalidTransitionError("Only SUBMITTED versions can be approved")
        if version.created_by.casefold() == actor.casefold():
            raise WorkflowValidationError(
                "The selection creator cannot approve the same version"
            )

        approved = self.repository.transition_version(
            selection_version_id,
            expected_status=SelectionStatus.SUBMITTED,
            target_status=SelectionStatus.APPROVED,
            actor=actor,
            comment=_optional_text(comment),
        )
        return {
            "selection_version": approved,
            "pipeline_run": self._trigger_downstream(approved, actor),
        }

    def trigger_downstream(
        self,
        selection_version_id: str,
        *,
        actor: str,
    ) -> dict[str, Any]:
        version = self._get_version(selection_version_id)
        if version.status != SelectionStatus.APPROVED:
            raise InvalidTransitionError(
                "Only APPROVED versions can trigger downstream processing"
            )
        return self._trigger_downstream(version, _required_text(actor, "actor"))

    def _trigger_downstream(
        self,
        approved: SelectionVersion,
        actor: str,
    ) -> dict[str, Any]:
        selection_version_id = approved.selection_version_id
        pipeline_run_id = str(uuid4())
        dag_run_id = f"selection__{selection_version_id}__{pipeline_run_id[:8]}"
        pipeline = {
            "pipeline_run_id": pipeline_run_id,
            "selection_version_id": selection_version_id,
            "model_run_id": approved.model_run_id,
            "airflow_dag_id": self.airflow_client.dag_id,
            "airflow_dag_run_id": dag_run_id,
            "status": "TRIGGERING",
            "triggered_by": actor,
            "triggered_at": datetime.now(timezone.utc),
            "error_message": None,
        }
        self.repository.record_pipeline_run(pipeline)
        try:
            trigger = self.airflow_client.trigger(
                dag_run_id=dag_run_id,
                conf={
                    "selection_version_id": selection_version_id,
                    "model_run_id": approved.model_run_id,
                    "pipeline_run_id": pipeline_run_id,
                    "approved_by": actor,
                },
            )
            self.repository.update_pipeline_run(
                pipeline_run_id,
                status=trigger.status,
            )
            pipeline["status"] = trigger.status
            pipeline["airflow_response"] = trigger.response
        except Exception as error:
            self.repository.update_pipeline_run(
                pipeline_run_id,
                status="TRIGGER_FAILED",
                error_message=str(error),
            )
            pipeline["status"] = "TRIGGER_FAILED"
            pipeline["error_message"] = str(error)
        return pipeline

    def reject(
        self,
        selection_version_id: str,
        *,
        actor: str,
        comment: str,
    ) -> SelectionVersion:
        version = self._get_version(selection_version_id)
        if version.status != SelectionStatus.SUBMITTED:
            raise InvalidTransitionError("Only SUBMITTED versions can be rejected")
        comment = _required_text(comment, "comment")
        return self.repository.transition_version(
            selection_version_id,
            expected_status=SelectionStatus.SUBMITTED,
            target_status=SelectionStatus.REJECTED,
            actor=_required_text(actor, "actor"),
            comment=comment,
        )

    def _get_version(self, selection_version_id: str) -> SelectionVersion:
        version = self.repository.get_version(selection_version_id)
        if version is None:
            raise WorkflowNotFoundError(
                f"Selection version {selection_version_id!r} was not found"
            )
        return version


def _selection_dict(selection: SelectionRecord) -> dict[str, Any]:
    record = asdict(selection)
    record["selection_source"] = selection.selection_source.value
    return record


def _selection_uniqueness_key(
    candidate_type: CandidateType,
    selection: SelectionRecord,
) -> tuple[Any, ...]:
    base = (
        selection.triangle_grain,
        selection.development_pool_id,
        selection.measure_type,
    )
    if candidate_type == CandidateType.LDF:
        assert isinstance(selection, LdfSelection)
        return base + (selection.from_age_months, selection.to_age_months)
    if candidate_type == CandidateType.TAIL:
        return base
    assert isinstance(selection, UltimateSelection)
    return base + (selection.accident_period,)


def _candidate_matches(
    candidate_type: CandidateType,
    selection: SelectionRecord,
    candidate: dict[str, Any],
) -> bool:
    common = (
        str(candidate.get("triangle_grain")) == selection.triangle_grain
        and str(candidate.get("development_pool_id"))
        == selection.development_pool_id
        and str(candidate.get("measure_type")) == selection.measure_type
    )
    if not common:
        return False
    if candidate_type == CandidateType.LDF:
        assert isinstance(selection, LdfSelection)
        return (
            int(candidate["from_age_months"]) == selection.from_age_months
            and int(candidate["to_age_months"]) == selection.to_age_months
            and str(candidate["development_method"]) == selection.selected_method
            and _same_number(candidate["candidate_ldf"], selection.selected_ldf)
        )
    if candidate_type == CandidateType.TAIL:
        assert isinstance(selection, TailSelection)
        return (
            str(candidate["development_method"]) == selection.development_method
            and str(candidate["tail_method"]) == selection.selected_tail_method
            and _same_number(candidate["tail_factor"], selection.selected_tail_factor)
        )
    assert isinstance(selection, UltimateSelection)
    return (
        _as_date(candidate["accident_period"]) == selection.accident_period
        and str(candidate["development_method"]) == selection.development_method
        and str(candidate["tail_method"]) == selection.tail_method
        and str(candidate["ultimate_method"]) == selection.selected_ultimate_method
        and _same_number(candidate["ultimate_value"], selection.selected_ultimate_value)
    )


def _validate_selected_value(
    candidate_type: CandidateType,
    selection: SelectionRecord,
) -> None:
    if candidate_type == CandidateType.LDF:
        value = selection.selected_ldf  # type: ignore[attr-defined]
        valid = math.isfinite(value) and value > 0
    elif candidate_type == CandidateType.TAIL:
        value = selection.selected_tail_factor  # type: ignore[attr-defined]
        valid = math.isfinite(value) and value >= 1
    else:
        value = selection.selected_ultimate_value  # type: ignore[attr-defined]
        valid = math.isfinite(value) and value >= 0
    if not valid:
        raise WorkflowValidationError(
            f"Invalid selected {candidate_type.value} value: {value}"
        )


def _scope_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["triangle_grain"]),
        str(row["development_pool_id"]),
        str(row["measure_type"]),
    )


def _same_number(left: Any, right: float) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _required_text(value: str | None, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise WorkflowValidationError(f"{field} is required")
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None
