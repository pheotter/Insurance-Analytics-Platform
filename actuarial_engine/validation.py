"""Structural validation for engine inputs."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import GRAIN_STEPS, MEASURE_COLUMNS


TRIANGLE_KEY = [
    "triangle_grain",
    "development_pool_id",
    "accident_period",
    "development_age_months",
]

REQUIRED_TRIANGLE_COLUMNS = {
    "triangle_grain",
    "development_pool_id",
    "pool_level",
    "line_of_business",
    "accident_period",
    "development_age_months",
    "valuation_date",
}


class TriangleValidationError(ValueError):
    """Raised when triangle structure cannot support reliable calculations."""


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    row_count: int = 0


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with trimmed lower-case column names."""

    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in frame.columns]
    return normalized


def validate_triangle(
    triangle: pd.DataFrame,
    *,
    measures: tuple[str, ...],
) -> list[ValidationIssue]:
    """Validate fatal triangle requirements and return non-fatal issues."""

    frame = normalize_columns(triangle)
    measure_columns = {MEASURE_COLUMNS[measure] for measure in measures}
    if "paid_and_expense" in measures:
        measure_columns.remove(MEASURE_COLUMNS["paid_and_expense"])
        measure_columns.update({"cumulative_paid_loss", "cumulative_paid_expense"})
    required = REQUIRED_TRIANGLE_COLUMNS | measure_columns
    missing = sorted(required - set(frame.columns))
    if missing:
        raise TriangleValidationError(
            f"Triangle is missing required columns: {', '.join(missing)}"
        )

    null_key_counts = frame[TRIANGLE_KEY].isna().sum()
    null_keys = null_key_counts[null_key_counts > 0]
    if not null_keys.empty:
        details = ", ".join(f"{key}={count}" for key, count in null_keys.items())
        raise TriangleValidationError(f"Triangle contains null calculation keys: {details}")

    duplicates = frame.duplicated(TRIANGLE_KEY, keep=False)
    if duplicates.any():
        raise TriangleValidationError(
            f"Triangle contains {int(duplicates.sum())} rows with duplicate grain keys"
        )

    invalid_grains = sorted(set(frame["triangle_grain"]) - set(GRAIN_STEPS))
    if invalid_grains:
        raise TriangleValidationError(
            f"Triangle contains unsupported grains: {', '.join(invalid_grains)}"
        )

    ages = pd.to_numeric(frame["development_age_months"], errors="coerce")
    if ages.isna().any() or (ages < 0).any() or (ages % 1 != 0).any():
        raise TriangleValidationError(
            "development_age_months must contain non-negative integers"
        )

    issues: list[ValidationIssue] = []
    for measure in measures:
        column = MEASURE_COLUMNS[measure]
        if measure == "paid_and_expense":
            values = pd.to_numeric(
                frame["cumulative_paid_loss"], errors="coerce"
            ) + pd.to_numeric(frame["cumulative_paid_expense"], errors="coerce")
        else:
            values = pd.to_numeric(frame[column], errors="coerce")
        invalid_count = int(values.isna().sum())
        if invalid_count:
            issues.append(
                ValidationIssue(
                    "WARNING",
                    "NON_NUMERIC_MEASURE",
                    f"{column} contains null or non-numeric values",
                    invalid_count,
                )
            )
        negative_count = int((values < 0).sum())
        if negative_count:
            issues.append(
                ValidationIssue(
                    "WARNING",
                    "NEGATIVE_CUMULATIVE_VALUE",
                    f"{column} contains negative cumulative values",
                    negative_count,
                )
            )

    return issues


def validate_expected_input(expected_input: pd.DataFrame | None) -> list[ValidationIssue]:
    """Describe optional expected-value input limitations without failing a run."""

    if expected_input is None or expected_input.empty:
        return [
            ValidationIssue(
                "WARNING",
                "MISSING_EXPECTED_INPUT",
                "Exposure-based and apriori methods may be unavailable",
            )
        ]

    frame = normalize_columns(expected_input)
    required_keys = {"development_pool_id", "accident_period"}
    missing = sorted(required_keys - set(frame.columns))
    if missing:
        raise TriangleValidationError(
            f"Expected input is missing required columns: {', '.join(missing)}"
        )

    key_columns = ["development_pool_id", "accident_period"]
    for optional_key in ("triangle_grain", "measure_type"):
        if optional_key in frame.columns:
            key_columns.append(optional_key)
    duplicates = frame.duplicated(key_columns, keep=False)
    if duplicates.any():
        raise TriangleValidationError(
            f"Expected input contains {int(duplicates.sum())} rows with duplicate keys"
        )
    return []
