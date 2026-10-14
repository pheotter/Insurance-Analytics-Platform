"""Runtime dependency construction for the API layer."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastapi import Header, HTTPException

from actuarial_workflow.airflow_client import AirflowRestClient
from actuarial_workflow.services import ApprovalService, SelectionService
from actuarial_workflow.snowflake_repository import SnowflakeWorkflowRepository


@dataclass(frozen=True)
class Actor:
    name: str
    role: str


def get_actor(
    x_actuarial_user: str = Header(...),
    x_actuarial_role: str = Header("actuary"),
) -> Actor:
    name = x_actuarial_user.strip()
    role = x_actuarial_role.strip().lower()
    if not name:
        raise HTTPException(status_code=401, detail="Missing actuarial user")
    if role not in {"actuary", "reviewer", "admin", "viewer"}:
        raise HTTPException(status_code=403, detail="Unsupported actuarial role")
    return Actor(name=name, role=role)


def require_reviewer(actor: Actor) -> Actor:
    if actor.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer role is required")
    return actor


@lru_cache(maxsize=1)
def get_repository() -> SnowflakeWorkflowRepository:
    return SnowflakeWorkflowRepository.from_environment()


def get_selection_service() -> SelectionService:
    return SelectionService(get_repository())


def get_approval_service() -> ApprovalService:
    return ApprovalService(
        get_repository(),
        AirflowRestClient.from_environment(),
    )
