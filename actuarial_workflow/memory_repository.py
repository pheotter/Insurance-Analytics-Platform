"""In-memory workflow adapter for unit tests and local service demonstrations."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from .domain import CandidateType, SelectionStatus, SelectionVersion
from .errors import InvalidTransitionError


class InMemoryWorkflowRepository:
    def __init__(
        self,
        *,
        model_runs: list[dict[str, Any]] | None = None,
        candidates: dict[CandidateType, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.model_runs = list(model_runs or [])
        self.candidates = {
            kind: list((candidates or {}).get(kind, [])) for kind in CandidateType
        }
        self.versions: dict[str, SelectionVersion] = {}
        self.selections: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self.events: list[dict[str, Any]] = []
        self.pipeline_runs: dict[str, dict[str, Any]] = {}

    def list_model_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.model_runs[:limit]

    def list_candidates(
        self,
        candidate_type: CandidateType,
        model_run_id: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = 10_000,
    ) -> list[dict[str, Any]]:
        rows = [
            row
            for row in self.candidates[candidate_type]
            if row["model_run_id"] == model_run_id
        ]
        for key, value in (filters or {}).items():
            if value:
                rows = [row for row in rows if str(row.get(key)) == value]
        return [dict(row) for row in rows[:limit]]

    def create_version(
        self,
        version: SelectionVersion,
        *,
        actor: str,
    ) -> SelectionVersion:
        self.versions[version.selection_version_id] = version
        self.selections[version.selection_version_id] = {
            kind.value: [] for kind in CandidateType
        }
        self.events.append({"event_type": "CREATED", "actor": actor})
        return version

    def get_version(self, selection_version_id: str) -> SelectionVersion | None:
        return self.versions.get(selection_version_id)

    def list_versions(
        self,
        *,
        status: SelectionStatus | None = None,
        limit: int = 100,
    ) -> list[SelectionVersion]:
        versions = sorted(
            self.versions.values(), key=lambda item: item.created_at, reverse=True
        )
        if status is not None:
            versions = [version for version in versions if version.status == status]
        return versions[:limit]

    def replace_selections(
        self,
        candidate_type: CandidateType,
        selection_version_id: str,
        records: list[dict[str, Any]],
        *,
        actor: str,
    ) -> None:
        self.selections[selection_version_id][candidate_type.value] = [
            dict(record) for record in records
        ]
        self.events.append(
            {
                "event_type": f"{candidate_type.value.upper()}_SELECTIONS_REPLACED",
                "actor": actor,
                "row_count": len(records),
            }
        )

    def get_selections(
        self,
        selection_version_id: str,
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            kind: [dict(record) for record in records]
            for kind, records in self.selections[selection_version_id].items()
        }

    def transition_version(
        self,
        selection_version_id: str,
        *,
        expected_status: SelectionStatus,
        target_status: SelectionStatus,
        actor: str,
        comment: str | None,
    ) -> SelectionVersion:
        current = self.versions[selection_version_id]
        if current.status != expected_status:
            raise InvalidTransitionError(
                f"Expected {expected_status.value}, got {current.status.value}"
            )
        now = datetime.now(timezone.utc)
        updates: dict[str, Any] = {
            "status": target_status,
            "review_comment": comment,
            "row_version": current.row_version + 1,
        }
        if target_status == SelectionStatus.SUBMITTED:
            updates.update(submitted_by=actor, submitted_at=now)
        elif target_status == SelectionStatus.APPROVED:
            updates.update(approved_by=actor, approved_at=now)
        elif target_status == SelectionStatus.REJECTED:
            updates.update(rejected_by=actor, rejected_at=now)
        updated = replace(current, **updates)
        self.versions[selection_version_id] = updated
        self.events.append(
            {
                "event_type": target_status.value,
                "actor": actor,
                "comment": comment,
            }
        )
        return updated

    def record_pipeline_run(self, record: dict[str, Any]) -> None:
        self.pipeline_runs[record["pipeline_run_id"]] = dict(record)

    def update_pipeline_run(
        self,
        pipeline_run_id: str,
        *,
        status: str,
        error_message: str | None = None,
    ) -> None:
        self.pipeline_runs[pipeline_run_id].update(
            status=status,
            error_message=error_message,
            updated_at=datetime.now(timezone.utc),
        )
