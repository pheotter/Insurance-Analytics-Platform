from __future__ import annotations

import pytest

from actuarial_engine.development import (
    build_ldf_observations,
    calculate_ldf_candidates,
)
from actuarial_engine.triangle import prepare_triangle


def test_builds_only_exact_adjacent_age_observations(
    cumulative_triangle, full_config
):
    prepared, _ = prepare_triangle(
        cumulative_triangle,
        as_of_date=full_config.as_of_date,
        triangle_grains=full_config.triangle_grains,
        measures=full_config.measures,
    )
    observations = build_ldf_observations(prepared)

    assert set(observations["to_age_months"] - observations["from_age_months"]) == {
        12
    }
    assert len(observations.loc[observations["from_age_months"] == 12]) == 3
    assert len(observations.loc[observations["from_age_months"] == 24]) == 2
    assert len(observations.loc[observations["from_age_months"] == 36]) == 1


def test_calculates_development_methods(cumulative_triangle, full_config):
    prepared, _ = prepare_triangle(
        cumulative_triangle,
        as_of_date=full_config.as_of_date,
        triangle_grains=full_config.triangle_grains,
        measures=full_config.measures,
    )
    observations = build_ldf_observations(prepared)
    candidates = calculate_ldf_candidates(prepared, observations, full_config)
    age_12 = candidates.loc[candidates["from_age_months"] == 12].set_index(
        "development_method"
    )

    assert age_12.loc["simple_average", "candidate_ldf"] == pytest.approx(1.5)
    assert age_12.loc["volume_weighted", "candidate_ldf"] == pytest.approx(1.5)
    assert age_12.loc["recent_3_weighted", "candidate_ldf"] == pytest.approx(1.5)
    assert age_12.loc["regression", "candidate_ldf"] == pytest.approx(1.5)
    assert age_12.loc["recent_3_weighted", "observation_count"] == 3

    age_24_recent = candidates.loc[
        (candidates["from_age_months"] == 24)
        & (candidates["development_method"] == "recent_3_weighted")
    ].iloc[0]
    assert age_24_recent["status"] == "NOT_AVAILABLE"
    assert age_24_recent["warning_message"] == "REQUIRES_3_RECENT_PERIODS"
