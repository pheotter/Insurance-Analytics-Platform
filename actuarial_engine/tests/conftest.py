from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from actuarial_engine.config import EngineConfig


@pytest.fixture
def cumulative_triangle() -> pd.DataFrame:
    values = {
        2020: {12: 100.0, 24: 150.0, 36: 180.0, 48: 198.0},
        2021: {12: 120.0, 24: 180.0, 36: 216.0},
        2022: {12: 140.0, 24: 210.0},
        2023: {12: 160.0},
    }
    rows = []
    for year, age_values in values.items():
        accident_period = pd.Timestamp(year=year, month=1, day=1)
        for age, value in age_values.items():
            valuation_date = accident_period + pd.DateOffset(months=age) - pd.Timedelta(
                days=1
            )
            rows.append(
                {
                    "triangle_grain": "annual",
                    "development_pool_id": "PA_BI",
                    "pool_level": "coverage",
                    "line_of_business": "personal_auto",
                    "accident_period": accident_period,
                    "development_age_months": age,
                    "valuation_date": valuation_date,
                    "cumulative_paid_loss": value * 0.8,
                    "cumulative_paid_expense": value * 0.05,
                    "cumulative_incurred_loss": value,
                    "cumulative_reported_claim_count": value / 10.0,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def expected_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "triangle_grain": ["annual"] * 4,
            "development_pool_id": ["PA_BI"] * 4,
            "measure_type": ["incurred"] * 4,
            "accident_period": pd.to_datetime(
                ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]
            ),
            "exposure_base": [1000.0] * 4,
            "expected_loss_ratio": [0.2] * 4,
        }
    )


@pytest.fixture
def full_config() -> EngineConfig:
    return EngineConfig(
        as_of_date=date(2023, 12, 31),
        development_methods=(
            "simple_average",
            "volume_weighted",
            "recent_3_weighted",
            "regression",
        ),
        tail_methods=("none", "constant", "curve", "bondy"),
        ultimate_methods=(
            "chainladder",
            "mack_chainladder",
            "bornhuetter_ferguson",
            "cape_cod",
            "benktander",
            "expected_loss",
        ),
        constant_tail_factor=1.05,
    )
