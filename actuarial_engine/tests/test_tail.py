from __future__ import annotations

import pytest

from actuarial_engine.development import (
    build_ldf_observations,
    calculate_ldf_candidates,
)
from actuarial_engine.tail import calculate_tail_candidates
from actuarial_engine.triangle import prepare_triangle


def test_calculates_package_none_constant_curve_and_bondy_tails(
    cumulative_triangle, full_config
):
    prepared, _ = prepare_triangle(
        cumulative_triangle,
        as_of_date=full_config.as_of_date,
        triangle_grains=full_config.triangle_grains,
        measures=full_config.measures,
    )
    observations = build_ldf_observations(prepared)
    candidates = calculate_ldf_candidates(prepared, observations, full_config)

    tails = calculate_tail_candidates(prepared, candidates, full_config)
    tails = tails.loc[
        tails["development_method"] == "volume_weighted"
    ].set_index("tail_method")

    assert tails.loc["none", "tail_factor"] == 1.0
    assert tails.loc["constant", "tail_factor"] == pytest.approx(1.05)
    assert tails.loc["curve", "tail_factor"] > 1.0
    assert tails.loc["curve", "status"] == "AVAILABLE"
    assert tails.loc["bondy", "tail_factor"] == pytest.approx(1.1)
    assert tails.loc["bondy", "bondy_exponent"] == pytest.approx(0.5)
