"""Run metadata and warehouse-oriented result formatting."""

from __future__ import annotations

from datetime import date, datetime, timezone

import chainladder
import pandas as pd


def add_run_metadata(
    frame: pd.DataFrame,
    *,
    model_run_id: str,
    as_of_date: date,
    engine_name: str,
    engine_version: str,
    created_at: datetime | None = None,
) -> pd.DataFrame:
    """Prepend reproducibility metadata to an engine result frame."""

    result = frame.copy()
    timestamp = created_at or datetime.now(timezone.utc)
    metadata = {
        "model_run_id": model_run_id,
        "as_of_date": pd.Timestamp(as_of_date),
        "engine_name": engine_name,
        "engine_version": engine_version,
        "calculation_library": "chainladder",
        "calculation_library_version": chainladder.__version__,
        "created_at": timestamp,
    }
    for position, (column, value) in enumerate(metadata.items()):
        result.insert(position, column, value)
    return result


def to_snowflake_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """
        Return an output copy using unquoted Snowflake-style column names.
        Return Pandas DataFrame copy, keep all the data, index, column order in the DataFrame
        Only modify the column name to capital
    """

    output = frame.copy()
    output.columns = [column.upper() for column in output.columns]
    return output
