from __future__ import annotations

import pandas as pd
import pytest

from actuarial_engine.io import validate_identifier
from actuarial_engine.triangle import prepare_triangle
from actuarial_engine.validation import TriangleValidationError, validate_expected_input


def test_rejects_duplicate_triangle_keys(cumulative_triangle, full_config):
    duplicate = cumulative_triangle.iloc[[0]]
    invalid = cumulative_triangle._append(duplicate, ignore_index=True)

    with pytest.raises(TriangleValidationError, match="duplicate grain keys"):
        prepare_triangle(
            invalid,
            as_of_date=full_config.as_of_date,
            triangle_grains=full_config.triangle_grains,
            measures=full_config.measures,
        )


def test_normalizes_snowflake_uppercase_columns(cumulative_triangle, full_config):
    uppercase = cumulative_triangle.copy()
    uppercase.columns = [column.upper() for column in uppercase.columns]

    prepared, _ = prepare_triangle(
        uppercase,
        as_of_date=full_config.as_of_date,
        triangle_grains=full_config.triangle_grains,
        measures=full_config.measures,
    )

    assert not prepared.empty
    assert "cumulative_value" in prepared.columns


def test_rejects_unsafe_warehouse_identifier():
    assert validate_identifier("ACTUARIAL_MODEL_CANDIDATE") == (
        "ACTUARIAL_MODEL_CANDIDATE"
    )
    with pytest.raises(ValueError, match="Unsafe Snowflake identifier"):
        validate_identifier("MODEL; DROP TABLE CLAIMS")


def test_rejects_duplicate_expected_value_keys(expected_input):
    duplicate = pd.concat([expected_input, expected_input.iloc[[0]]], ignore_index=True)

    with pytest.raises(TriangleValidationError, match="duplicate keys"):
        validate_expected_input(duplicate)
