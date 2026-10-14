"""Adapters from warehouse triangle contracts to engine calculation frames."""

from __future__ import annotations

from datetime import date

import pandas as pd

from .config import GRAIN_STEPS, MEASURE_COLUMNS
from .validation import ValidationIssue, normalize_columns, validate_triangle


IDENTITY_COLUMNS = [
    "triangle_grain",
    "development_pool_id",
    "pool_level",
    "line_of_business",
    "accident_period",
    "development_age_months",
    "valuation_date",
]


def prepare_triangle(
    triangle: pd.DataFrame,
    *,
    as_of_date: date,
    triangle_grains: tuple[str, ...],
    measures: tuple[str, ...],
) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    """Normalize, validate, filter, and reshape a cumulative triangle."""

    issues = validate_triangle(triangle, measures=measures)
    frame = normalize_columns(triangle)
    frame["accident_period"] = pd.to_datetime(frame["accident_period"]).dt.normalize()
    frame["valuation_date"] = pd.to_datetime(frame["valuation_date"]).dt.normalize()
    frame["development_age_months"] = frame["development_age_months"].astype(int)

    cutoff = pd.Timestamp(as_of_date)
    future_count = int((frame["valuation_date"] > cutoff).sum())
    if future_count:
        issues.append(
            ValidationIssue(
                "INFO",
                "FUTURE_VALUATIONS_FILTERED",
                "Rows after the requested as-of date were excluded",
                future_count,
            )
        )

    frame = frame.loc[
        frame["triangle_grain"].isin(triangle_grains)
        & (frame["valuation_date"] <= cutoff)
    ].copy()
    if frame.empty:
        raise ValueError("No triangle rows remain after grain and as-of-date filtering")

    value_columns: list[str] = []
    rename_map: dict[str, str] = {}
    if "paid_and_expense" in measures:
        paid_expense_column = MEASURE_COLUMNS["paid_and_expense"]
        if paid_expense_column not in frame.columns:
            frame[paid_expense_column] = (
                pd.to_numeric(frame["cumulative_paid_loss"], errors="coerce")
                + pd.to_numeric(frame["cumulative_paid_expense"], errors="coerce")
            )

    for measure in measures:
        column = MEASURE_COLUMNS[measure]
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        value_columns.append(column)
        rename_map[column] = measure

    long_frame = frame.melt(
        id_vars=IDENTITY_COLUMNS,
        value_vars=value_columns,
        var_name="measure_column",
        value_name="cumulative_value",
    )
    long_frame["measure_type"] = long_frame["measure_column"].map(rename_map)
    long_frame["development_step_months"] = long_frame["triangle_grain"].map(
        GRAIN_STEPS
    )
    long_frame = long_frame.drop(columns="measure_column")

    return long_frame.sort_values(
        [
            "triangle_grain",
            "development_pool_id",
            "measure_type",
            "accident_period",
            "development_age_months",
        ]
    ).reset_index(drop=True), issues


def latest_diagonal(triangle: pd.DataFrame) -> pd.DataFrame:
    """Return the latest available cumulative value for every accident period."""

    group_columns = [
        "triangle_grain",
        "development_pool_id",
        "pool_level",
        "line_of_business",
        "measure_type",
        "accident_period",
    ]
    latest_index = triangle.groupby(group_columns, dropna=False)[
        "development_age_months"
    ].idxmax()
    latest = triangle.loc[latest_index].copy()
    return latest.rename(
        columns={
            "development_age_months": "latest_development_age",
            "cumulative_value": "latest_observed_value",
        }
    )[
        group_columns
        + ["latest_development_age", "latest_observed_value", "valuation_date"]
    ].reset_index(drop=True)
