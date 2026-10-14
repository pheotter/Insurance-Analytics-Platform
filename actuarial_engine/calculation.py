"""UI-independent orchestration for one actuarial candidate run."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from .config import EngineConfig
from .development import build_ldf_observations, calculate_ldf_candidates
from .result_formatter import add_run_metadata
from .tail import calculate_tail_candidates
from .triangle import latest_diagonal, prepare_triangle
from .ultimate import calculate_model_candidates
from .validation import ValidationIssue, validate_expected_input


@dataclass(frozen=True)
class EngineRunResult:
    model_run_id: str
    ldf_observations: pd.DataFrame
    ldf_candidates: pd.DataFrame
    tail_candidates: pd.DataFrame
    model_candidates: pd.DataFrame
    diagnostics: pd.DataFrame


def run_modeling(
    triangle: pd.DataFrame,
    *,
    config: EngineConfig,
    expected_input: pd.DataFrame | None = None,
    model_run_id: str | None = None,
) -> EngineRunResult:
    """Validate inputs and calculate all configured actuarial candidates."""

    run_id = model_run_id or str(uuid4())
    created_at = datetime.now(timezone.utc)
    prepared, issues = prepare_triangle(
        triangle,
        as_of_date=config.as_of_date,
        triangle_grains=config.triangle_grains,
        measures=config.measures,
    )
    issues.extend(validate_expected_input(expected_input))

    observations = build_ldf_observations(prepared)
    ldf_candidates = calculate_ldf_candidates(prepared, observations, config)
    tail_candidates = calculate_tail_candidates(prepared, ldf_candidates, config)
    model_candidates = calculate_model_candidates(
        prepared,
        latest_diagonal(prepared),
        ldf_candidates,
        tail_candidates,
        expected_input,
        config,
    )

    diagnostics = _build_diagnostics(
        issues, observations, ldf_candidates, tail_candidates, model_candidates
    )
    metadata = {
        "model_run_id": run_id,
        "as_of_date": config.as_of_date,
        "engine_name": config.engine_name,
        "engine_version": config.engine_version,
        "created_at": created_at,
    }
    return EngineRunResult(
        model_run_id=run_id,
        ldf_observations=add_run_metadata(observations, **metadata),
        ldf_candidates=add_run_metadata(ldf_candidates, **metadata),
        tail_candidates=add_run_metadata(tail_candidates, **metadata),
        model_candidates=add_run_metadata(model_candidates, **metadata),
        diagnostics=add_run_metadata(diagnostics, **metadata),
    )


def _build_diagnostics(
    issues: list[ValidationIssue],
    observations: pd.DataFrame,
    ldf_candidates: pd.DataFrame,
    tail_candidates: pd.DataFrame,
    model_candidates: pd.DataFrame,
) -> pd.DataFrame:
    rows = [issue.__dict__ for issue in issues]
    excluded = int((~observations["is_eligible"]).sum()) if not observations.empty else 0
    if excluded:
        rows.append(
            {
                "severity": "WARNING",
                "code": "EXCLUDED_LDF_OBSERVATIONS",
                "message": "Observations with invalid denominators were excluded",
                "row_count": excluded,
            }
        )
    for name, frame in (
        ("LDF_CANDIDATE", ldf_candidates),
        ("TAIL_CANDIDATE", tail_candidates),
        ("MODEL_CANDIDATE", model_candidates),
    ):
        unavailable = int((frame["status"] == "NOT_AVAILABLE").sum())
        rows.append(
            {
                "severity": "INFO" if unavailable == 0 else "WARNING",
                "code": f"{name}_NOT_AVAILABLE",
                "message": f"{name.replace('_', ' ').title()} availability summary",
                "row_count": unavailable,
            }
        )
    return pd.DataFrame(rows, columns=["severity", "code", "message", "row_count"])
