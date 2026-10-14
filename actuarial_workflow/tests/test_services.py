from __future__ import annotations

from datetime import date

import pytest

from actuarial_workflow.airflow_client import AirflowTriggerResult
from actuarial_workflow.domain import (
    CandidateType,
    LdfSelection,
    SelectionSource,
    SelectionStatus,
    TailSelection,
    UltimateSelection,
)
from actuarial_workflow.errors import (
    InvalidTransitionError,
    WorkflowValidationError,
)
from actuarial_workflow.memory_repository import InMemoryWorkflowRepository
from actuarial_workflow.services import ApprovalService, SelectionService


MODEL_RUN_ID = "model-run-1"


class FakeAirflowClient:
    dag_id = "approved_actuarial_pricing"

    def __init__(self) -> None:
        self.calls = []

    def trigger(self, *, dag_run_id, conf):
        self.calls.append((dag_run_id, conf))
        return AirflowTriggerResult(dag_run_id, "QUEUED", {"state": "queued"})


@pytest.fixture
def repository():
    common = {
        "model_run_id": MODEL_RUN_ID,
        "triangle_grain": "annual",
        "development_pool_id": "PA_BI",
        "pool_level": "coverage",
        "line_of_business": "personal_auto",
        "status": "AVAILABLE",
    }
    candidates = {
        CandidateType.LDF: [
            {
                **common,
                "measure_type": measure,
                "from_age_months": 12,
                "to_age_months": 24,
                "development_method": "volume_weighted",
                "candidate_ldf": 1.5,
            }
            for measure in ("incurred", "reported_count")
        ],
        CandidateType.TAIL: [
            {
                **common,
                "measure_type": measure,
                "development_method": "volume_weighted",
                "tail_method": "none",
                "tail_factor": 1.0,
            }
            for measure in ("incurred", "reported_count")
        ],
        CandidateType.ULTIMATE: [
            {
                **common,
                "measure_type": measure,
                "accident_period": date(2023, 1, 1),
                "development_method": "volume_weighted",
                "tail_method": "none",
                "ultimate_method": "chainladder",
                "ultimate_value": value,
            }
            for measure, value in (("incurred", 1_000.0), ("reported_count", 10.0))
        ],
    }
    return InMemoryWorkflowRepository(
        model_runs=[
            {
                "model_run_id": MODEL_RUN_ID,
                "as_of_date": date(2023, 12, 31),
            }
        ],
        candidates=candidates,
    )


def populate_selection(service: SelectionService, version_id: str) -> None:
    service.replace_ldf_selections(
        version_id,
        [
            LdfSelection(
                triangle_grain="annual",
                development_pool_id="PA_BI",
                pool_level="coverage",
                line_of_business="personal_auto",
                measure_type=measure,
                from_age_months=12,
                to_age_months=24,
                selected_method="volume_weighted",
                selected_ldf=1.5,
            )
            for measure in ("incurred", "reported_count")
        ],
        actor="actuary.one",
    )
    service.replace_tail_selections(
        version_id,
        [
            TailSelection(
                triangle_grain="annual",
                development_pool_id="PA_BI",
                pool_level="coverage",
                line_of_business="personal_auto",
                measure_type=measure,
                development_method="volume_weighted",
                selected_tail_method="none",
                selected_tail_factor=1.0,
            )
            for measure in ("incurred", "reported_count")
        ],
        actor="actuary.one",
    )
    service.replace_ultimate_selections(
        version_id,
        [
            UltimateSelection(
                triangle_grain="annual",
                development_pool_id="PA_BI",
                pool_level="coverage",
                line_of_business="personal_auto",
                measure_type=measure,
                accident_period=date(2023, 1, 1),
                development_method="volume_weighted",
                tail_method="none",
                selected_ultimate_method="chainladder",
                selected_ultimate_value=value,
            )
            for measure, value in (("incurred", 1_000.0), ("reported_count", 10.0))
        ],
        actor="actuary.one",
    )


def test_selection_submission_and_independent_approval(repository):
    selections = SelectionService(repository)
    airflow = FakeAirflowClient()
    approvals = ApprovalService(repository, airflow)
    version = selections.create_version(
        model_run_id=MODEL_RUN_ID,
        actor="actuary.one",
    )
    populate_selection(selections, version.selection_version_id)

    submitted = selections.submit(
        version.selection_version_id,
        actor="actuary.one",
        comment="Ready for review",
    )
    assert submitted.status == SelectionStatus.SUBMITTED

    with pytest.raises(WorkflowValidationError, match="cannot approve"):
        approvals.approve(
            version.selection_version_id,
            actor="actuary.one",
        )

    result = approvals.approve(
        version.selection_version_id,
        actor="reviewer.one",
        comment="Reviewed",
    )
    assert result["selection_version"].status == SelectionStatus.APPROVED
    assert result["pipeline_run"]["status"] == "QUEUED"
    assert airflow.calls[0][1]["selection_version_id"] == version.selection_version_id


def test_manual_override_requires_reason(repository):
    service = SelectionService(repository)
    version = service.create_version(model_run_id=MODEL_RUN_ID, actor="actuary.one")

    with pytest.raises(WorkflowValidationError, match="selection_reason"):
        service.replace_ldf_selections(
            version.selection_version_id,
            [
                LdfSelection(
                    triangle_grain="annual",
                    development_pool_id="PA_BI",
                    pool_level="coverage",
                    line_of_business="personal_auto",
                    measure_type="incurred",
                    from_age_months=12,
                    to_age_months=24,
                    selected_method="manual",
                    selected_ldf=1.4,
                    selection_source=SelectionSource.MANUAL_OVERRIDE,
                )
            ],
            actor="actuary.one",
        )


def test_submitted_version_is_immutable(repository):
    service = SelectionService(repository)
    version = service.create_version(model_run_id=MODEL_RUN_ID, actor="actuary.one")
    populate_selection(service, version.selection_version_id)
    service.submit(version.selection_version_id, actor="actuary.one")

    with pytest.raises(InvalidTransitionError, match="expected DRAFT"):
        service.replace_ldf_selections(
            version.selection_version_id,
            [
                LdfSelection(
                    triangle_grain="annual",
                    development_pool_id="PA_BI",
                    pool_level="coverage",
                    line_of_business="personal_auto",
                    measure_type="incurred",
                    from_age_months=12,
                    to_age_months=24,
                    selected_method="volume_weighted",
                    selected_ldf=1.5,
                )
            ],
            actor="actuary.one",
        )
