from __future__ import annotations

import chainladder
import pandas as pd
import pytest

from actuarial_engine.config import EngineConfig
from actuarial_engine.run_modeling import run_modeling


def test_runs_all_ultimate_methods(cumulative_triangle, expected_input, full_config):
    result = run_modeling(
        cumulative_triangle,
        config=full_config,
        expected_input=expected_input,
        model_run_id="test-run",
    )
    models = result.model_candidates

    assert set(models["ultimate_method"]) == set(full_config.ultimate_methods)
    assert set(models["development_method"]) == set(full_config.development_methods)
    assert set(models["tail_method"]) == set(full_config.tail_methods)
    assert set(models["model_run_id"]) == {"test-run"}
    assert set(models["calculation_library"]) == {"chainladder"}
    assert set(models["calculation_library_version"]) == {chainladder.__version__}


def test_ultimate_formulas_for_latest_origin(cumulative_triangle, expected_input):
    config = EngineConfig(
        as_of_date=pd.Timestamp("2023-12-31").date(),
        development_methods=("volume_weighted",),
        tail_methods=("none",),
        ultimate_methods=(
            "chainladder",
            "bornhuetter_ferguson",
            "cape_cod",
            "benktander",
            "expected_loss",
        ),
    )
    result = run_modeling(
        cumulative_triangle,
        config=config,
        expected_input=expected_input,
        model_run_id="formula-run",
    )
    latest = result.model_candidates.loc[
        result.model_candidates["accident_period"] == pd.Timestamp("2023-01-01")
    ].set_index("ultimate_method")

    cdf = 1.5 * 1.2 * 1.1
    percent_unreported = 1.0 - 1.0 / cdf
    assert latest.loc["chainladder", "ultimate_value"] == pytest.approx(160.0 * cdf)
    assert latest.loc["bornhuetter_ferguson", "ultimate_value"] == pytest.approx(
        160.0 + 200.0 * percent_unreported
    )
    assert latest.loc["expected_loss", "ultimate_value"] == pytest.approx(200.0)
    assert latest.loc["benktander", "ultimate_value"] == pytest.approx(
        200.0 * percent_unreported**2 + 160.0 * (1.0 + percent_unreported)
    )
    assert latest.loc["cape_cod", "status"] == "AVAILABLE"


def test_missing_expected_input_is_reported_not_raised(cumulative_triangle):
    config = EngineConfig(
        as_of_date=pd.Timestamp("2023-12-31").date(),
        development_methods=("volume_weighted",),
        tail_methods=("none",),
        ultimate_methods=(
            "chainladder",
            "bornhuetter_ferguson",
            "cape_cod",
            "benktander",
            "expected_loss",
        ),
    )

    result = run_modeling(cumulative_triangle, config=config)
    status = result.model_candidates.groupby("ultimate_method")["status"].unique()

    assert set(status["chainladder"]) == {"AVAILABLE"}
    for method in (
        "bornhuetter_ferguson",
        "cape_cod",
        "benktander",
        "expected_loss",
    ):
        assert set(status[method]) == {"NOT_AVAILABLE"}


def test_mack_rejects_non_volume_development(cumulative_triangle, expected_input):
    config = EngineConfig(
        as_of_date=pd.Timestamp("2023-12-31").date(),
        development_methods=("simple_average",),
        tail_methods=("none",),
        ultimate_methods=("mack_chainladder",),
    )

    result = run_modeling(
        cumulative_triangle, config=config, expected_input=expected_input
    )

    assert set(result.model_candidates["status"]) == {"NOT_AVAILABLE"}
    assert set(result.model_candidates["warning_message"]) == {
        "MACK_REQUIRES_VOLUME_WEIGHTED_DEVELOPMENT"
    }
