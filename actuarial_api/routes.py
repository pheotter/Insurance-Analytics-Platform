"""Versioned HTTP routes for candidate review and approval."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from actuarial_workflow.domain import (
    CandidateType,
    LdfSelection,
    SelectionStatus,
    TailSelection,
    UltimateSelection,
)
from actuarial_workflow.services import ApprovalService, SelectionService

from .dependencies import (
    Actor,
    get_actor,
    get_approval_service,
    get_selection_service,
    require_reviewer,
)
from .schemas import (
    CreateSelectionVersionRequest,
    RejectRequest,
    ReplaceLdfSelectionsRequest,
    ReplaceTailSelectionsRequest,
    ReplaceUltimateSelectionsRequest,
    ReviewActionRequest,
)


router = APIRouter(prefix="/api/v1")
SelectionDependency = Annotated[SelectionService, Depends(get_selection_service)]
ApprovalDependency = Annotated[ApprovalService, Depends(get_approval_service)]
ActorDependency = Annotated[Actor, Depends(get_actor)]


@router.get("/model-runs")
def list_model_runs(
    service: SelectionDependency,
    limit: int = Query(100, ge=1, le=1_000),
) -> list[dict]:
    return jsonable_encoder(service.list_model_runs(limit=limit))


@router.get("/model-runs/{model_run_id}/candidates/{candidate_type}")
def list_candidates(
    model_run_id: str,
    candidate_type: CandidateType,
    service: SelectionDependency,
    triangle_grain: str | None = None,
    development_pool_id: str | None = None,
    line_of_business: str | None = None,
    measure_type: str | None = None,
    limit: int = Query(10_000, ge=1, le=100_000),
) -> list[dict]:
    filters = {
        "triangle_grain": triangle_grain,
        "development_pool_id": development_pool_id,
        "line_of_business": line_of_business,
        "measure_type": measure_type,
    }
    return jsonable_encoder(
        service.list_candidates(
            candidate_type,
            model_run_id,
            filters={key: value for key, value in filters.items() if value},
            limit=limit,
        )
    )


@router.post("/selection-versions", status_code=201)
def create_selection_version(
    request: CreateSelectionVersionRequest,
    service: SelectionDependency,
    actor: ActorDependency,
) -> dict:
    return jsonable_encoder(
        service.create_version(
            model_run_id=request.model_run_id,
            actor=actor.name,
            comment=request.comment,
        )
    )


@router.get("/selection-versions")
def list_selection_versions(
    service: SelectionDependency,
    status: SelectionStatus | None = None,
    limit: int = Query(100, ge=1, le=1_000),
) -> list[dict]:
    return jsonable_encoder(service.list_versions(status=status, limit=limit))


@router.get("/selection-versions/{selection_version_id}")
def get_selection_version(
    selection_version_id: str,
    service: SelectionDependency,
) -> dict:
    return jsonable_encoder(
        {
            "selection_version": service.get_version(selection_version_id),
            "selections": service.get_selections(selection_version_id),
        }
    )


@router.put("/selection-versions/{selection_version_id}/ldf-selections")
def replace_ldf_selections(
    selection_version_id: str,
    request: ReplaceLdfSelectionsRequest,
    service: SelectionDependency,
    actor: ActorDependency,
) -> dict:
    service.replace_ldf_selections(
        selection_version_id,
        [LdfSelection(**item.model_dump()) for item in request.selections],
        actor=actor.name,
    )
    return {"status": "saved", "row_count": len(request.selections)}


@router.put("/selection-versions/{selection_version_id}/tail-selections")
def replace_tail_selections(
    selection_version_id: str,
    request: ReplaceTailSelectionsRequest,
    service: SelectionDependency,
    actor: ActorDependency,
) -> dict:
    service.replace_tail_selections(
        selection_version_id,
        [TailSelection(**item.model_dump()) for item in request.selections],
        actor=actor.name,
    )
    return {"status": "saved", "row_count": len(request.selections)}


@router.put("/selection-versions/{selection_version_id}/ultimate-selections")
def replace_ultimate_selections(
    selection_version_id: str,
    request: ReplaceUltimateSelectionsRequest,
    service: SelectionDependency,
    actor: ActorDependency,
) -> dict:
    service.replace_ultimate_selections(
        selection_version_id,
        [UltimateSelection(**item.model_dump()) for item in request.selections],
        actor=actor.name,
    )
    return {"status": "saved", "row_count": len(request.selections)}


@router.post("/selection-versions/{selection_version_id}/submit")
def submit_selection_version(
    selection_version_id: str,
    request: ReviewActionRequest,
    service: SelectionDependency,
    actor: ActorDependency,
) -> dict:
    return jsonable_encoder(
        service.submit(
            selection_version_id,
            actor=actor.name,
            comment=request.comment,
        )
    )


@router.post("/selection-versions/{selection_version_id}/approve")
def approve_selection_version(
    selection_version_id: str,
    request: ReviewActionRequest,
    service: ApprovalDependency,
    actor: ActorDependency,
) -> dict:
    require_reviewer(actor)
    return jsonable_encoder(
        service.approve(
            selection_version_id,
            actor=actor.name,
            comment=request.comment,
        )
    )


@router.post("/selection-versions/{selection_version_id}/reject")
def reject_selection_version(
    selection_version_id: str,
    request: RejectRequest,
    service: ApprovalDependency,
    actor: ActorDependency,
) -> dict:
    require_reviewer(actor)
    return jsonable_encoder(
        service.reject(
            selection_version_id,
            actor=actor.name,
            comment=request.comment,
        )
    )


@router.post("/selection-versions/{selection_version_id}/trigger")
def trigger_approved_selection(
    selection_version_id: str,
    service: ApprovalDependency,
    actor: ActorDependency,
) -> dict:
    require_reviewer(actor)
    return jsonable_encoder(
        service.trigger_downstream(selection_version_id, actor=actor.name)
    )
