"""FastAPI application for the actuarial review workflow."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from actuarial_workflow.errors import (
    InvalidTransitionError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)

from .routes import router


app = FastAPI(
    title="Actuarial Selection API",
    version="0.1.0",
    description="Governed LDF, tail, and ultimate selection workflow.",
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(WorkflowNotFoundError)
async def not_found_handler(
    _request: Request,
    error: WorkflowNotFoundError,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(InvalidTransitionError)
async def transition_handler(
    _request: Request,
    error: InvalidTransitionError,
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.exception_handler(WorkflowValidationError)
async def validation_handler(
    _request: Request,
    error: WorkflowValidationError,
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(error)})
