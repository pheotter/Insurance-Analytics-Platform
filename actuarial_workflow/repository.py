"""Persistence port for selection and approval workflows."""

from __future__ import annotations

from typing import Any, Protocol

from .domain import CandidateType, SelectionStatus, SelectionVersion


class WorkflowRepository(Protocol):
    def list_model_runs(self, *, limit: int = 100) -> list[dict[str, Any]]: ...

    def list_candidates(
        self,
        candidate_type: CandidateType,
        model_run_id: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = 10_000,
    ) -> list[dict[str, Any]]: ...

    def create_version(
        self,
        version: SelectionVersion,
        *,
        actor: str,
    ) -> SelectionVersion: ...

    def get_version(self, selection_version_id: str) -> SelectionVersion | None: ...

    def list_versions(
        self,
        *,
        status: SelectionStatus | None = None,
        limit: int = 100,
    ) -> list[SelectionVersion]: ...

    def replace_selections(
        self,
        candidate_type: CandidateType,
        selection_version_id: str,
        records: list[dict[str, Any]],
        *,
        actor: str,
    ) -> None: ...

    def get_selections(
        self,
        selection_version_id: str,
    ) -> dict[str, list[dict[str, Any]]]: ...

    def transition_version(
        self,
        selection_version_id: str,
        *,
        expected_status: SelectionStatus,
        target_status: SelectionStatus,
        actor: str,
        comment: str | None,
    ) -> SelectionVersion: ...

    def record_pipeline_run(self, record: dict[str, Any]) -> None: ...

    def update_pipeline_run(
        self,
        pipeline_run_id: str,
        *,
        status: str,
        error_message: str | None = None,
    ) -> None: ...
