"""Package-backed age-to-age observations and LDF candidates."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .chainladder_adapter import (
    build_triangle,
    fit_development,
    selected_ldf_values,
)
from .config import EngineConfig


DEVELOPMENT_GROUP = [
    "triangle_grain",
    "development_pool_id",
    "pool_level",
    "line_of_business",
    "measure_type",
]

AGE_GROUP = DEVELOPMENT_GROUP + ["from_age_months", "to_age_months"]


def build_ldf_observations(triangle: pd.DataFrame) -> pd.DataFrame:
    """Extract chainladder's observed link ratios into the platform contract."""

    rows: list[dict[str, object]] = []
    for key, group in triangle.groupby(DEVELOPMENT_GROUP, dropna=False):
        identity = dict(zip(DEVELOPMENT_GROUP, key, strict=True))
        package_triangle = build_triangle(group)
        ratios = package_triangle.link_ratio.to_frame(
            origin_as_datetime=True, keepdims=True
        ).reset_index(drop=True)
        value_column = _result_value_column(ratios)
        age_pairs = _age_pairs(package_triangle)
        value_lookup = {
            (
                pd.Timestamp(row.accident_period).normalize(),
                int(row.development_age_months),
            ): row
            for row in group.itertuples()
        }

        for ratio in ratios.to_dict("records"):
            from_age = int(ratio["development"])
            if from_age not in age_pairs:
                continue
            to_age = age_pairs[from_age]
            origin = pd.Timestamp(ratio["origin"]).normalize()
            from_row = value_lookup.get((origin, from_age))
            to_row = value_lookup.get((origin, to_age))
            if from_row is None or to_row is None:
                continue
            link_ratio = float(ratio[value_column])
            eligible = bool(np.isfinite(link_ratio))
            rows.append(
                {
                    **identity,
                    "accident_period": origin,
                    "from_age_months": from_age,
                    "to_age_months": to_age,
                    "from_value": float(from_row.cumulative_value),
                    "to_value": float(to_row.cumulative_value),
                    "link_ratio": link_ratio if eligible else math.nan,
                    "is_eligible": eligible,
                    "exclusion_reason": (
                        None if eligible else "CHAINLADDER_LINK_RATIO_NOT_FINITE"
                    ),
                    "from_valuation_date": from_row.valuation_date,
                    "to_valuation_date": to_row.valuation_date,
                }
            )

    columns = DEVELOPMENT_GROUP + [
        "accident_period",
        "from_age_months",
        "to_age_months",
        "from_value",
        "to_value",
        "link_ratio",
        "is_eligible",
        "exclusion_reason",
        "from_valuation_date",
        "to_valuation_date",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        DEVELOPMENT_GROUP
        + ["from_age_months", "to_age_months", "accident_period"]
    ).reset_index(drop=True)


def calculate_ldf_candidates(
    triangle: pd.DataFrame,
    observations: pd.DataFrame,
    config: EngineConfig,
) -> pd.DataFrame:
    """Fit chainladder Development estimators and format selected LDFs."""

    rows: list[dict[str, object]] = []
    for key, group in triangle.groupby(DEVELOPMENT_GROUP, dropna=False):
        identity = dict(zip(DEVELOPMENT_GROUP, key, strict=True))
        package_triangle = build_triangle(group)
        ages = [int(age) for age in package_triangle.development]
        fallback_pairs = list(zip(ages[:-1], ages[1:], strict=True))
        matching_observations = _match_identity(observations, identity)

        for method in config.development_methods:
            try:
                _, developed = fit_development(package_triangle, method, config)
                selected = selected_ldf_values(developed, package_triangle)
                error = None
            except Exception as exception:
                selected = [
                    (from_age, to_age, math.nan)
                    for from_age, to_age in fallback_pairs
                ]
                error = f"CHAINLADDER_DEVELOPMENT_ERROR: {exception}"

            for from_age, to_age, candidate in selected:
                count = int(
                    (
                        (matching_observations["from_age_months"] == from_age)
                        & (matching_observations["to_age_months"] == to_age)
                        & matching_observations["is_eligible"]
                    ).sum()
                )
                status, warning = _availability(
                    method, candidate, count, config, error
                )
                rows.append(
                    {
                        **identity,
                        "from_age_months": from_age,
                        "to_age_months": to_age,
                        "development_method": method,
                        "candidate_ldf": (
                            candidate if status == "AVAILABLE" else math.nan
                        ),
                        "observation_count": count,
                        "status": status,
                        "warning_message": warning,
                    }
                )

    columns = AGE_GROUP + [
        "development_method",
        "candidate_ldf",
        "observation_count",
        "status",
        "warning_message",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        DEVELOPMENT_GROUP
        + ["development_method", "from_age_months", "to_age_months"]
    ).reset_index(drop=True)


def _availability(
    method: str,
    candidate: float,
    observation_count: int,
    config: EngineConfig,
    error: str | None,
) -> tuple[str, str | None]:
    if error:
        return "NOT_AVAILABLE", error
    if not np.isfinite(candidate) or candidate <= 0:
        return "NOT_AVAILABLE", "CHAINLADDER_LDF_NOT_AVAILABLE"
    if method == "recent_3_weighted" and observation_count < config.recent_period_count:
        return (
            "NOT_AVAILABLE",
            f"REQUIRES_{config.recent_period_count}_RECENT_PERIODS",
        )
    if (
        method == "regression"
        and observation_count < config.minimum_regression_observations
    ):
        return "NOT_AVAILABLE", "INSUFFICIENT_REGRESSION_OBSERVATIONS"
    return "AVAILABLE", None


def _age_pairs(package_triangle: object) -> dict[int, int]:
    ages = [int(age) for age in package_triangle.development]
    return dict(zip(ages[:-1], ages[1:], strict=True))


def _result_value_column(frame: pd.DataFrame) -> str:
    candidates = [
        column for column in frame.columns if column not in {"origin", "development"}
    ]
    if len(candidates) != 1:
        raise ValueError(f"Expected one chainladder result column, found {candidates}")
    return candidates[0]


def _match_identity(frame: pd.DataFrame, identity: dict[str, object]) -> pd.DataFrame:
    match = pd.Series(True, index=frame.index)
    for column, value in identity.items():
        match &= frame[column] == value
    return frame.loc[match]
