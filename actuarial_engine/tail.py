"""Package-backed tail-factor candidates."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .chainladder_adapter import (
    build_triangle,
    fit_development,
    fit_tail,
    tail_diagnostics,
)
from .config import EngineConfig
from .development import DEVELOPMENT_GROUP


TAIL_GROUP = DEVELOPMENT_GROUP + ["development_method"]


def calculate_tail_candidates(
    triangle: pd.DataFrame,
    ldf_candidates: pd.DataFrame,
    config: EngineConfig,
) -> pd.DataFrame:
    """Apply chainladder tail transformers to each development pattern."""

    rows: list[dict[str, object]] = []
    for key, group in triangle.groupby(DEVELOPMENT_GROUP, dropna=False):
        identity = dict(zip(DEVELOPMENT_GROUP, key, strict=True))
        package_triangle = build_triangle(group)
        pool_ldfs = _match_identity(ldf_candidates, identity)

        for development_method in config.development_methods:
            method_ldfs = pool_ldfs.loc[
                pool_ldfs["development_method"] == development_method
            ]
            incomplete = method_ldfs.empty or (
                method_ldfs["status"] != "AVAILABLE"
            ).any()

            try:
                _, developed = fit_development(
                    package_triangle, development_method, config
                )
                development_error = None
            except Exception as exception:
                developed = None
                development_error = f"CHAINLADDER_DEVELOPMENT_ERROR: {exception}"

            for tail_method in config.tail_methods:
                status = "AVAILABLE"
                warning = None
                factor = math.nan
                slope = math.nan
                intercept = math.nan
                exponent = math.nan

                if development_error:
                    status = "NOT_AVAILABLE"
                    warning = development_error
                elif incomplete:
                    status = "NOT_AVAILABLE"
                    warning = "INCOMPLETE_DEVELOPMENT_PATTERN"
                else:
                    try:
                        estimator, _, factor = fit_tail(
                            developed, tail_method, config
                        )
                        slope, intercept, exponent = tail_diagnostics(estimator)
                        if not np.isfinite(factor) or factor < 1.0:
                            status = "NOT_AVAILABLE"
                            warning = "CHAINLADDER_TAIL_NOT_AVAILABLE"
                    except Exception as exception:
                        status = "NOT_AVAILABLE"
                        warning = f"CHAINLADDER_TAIL_ERROR: {exception}"

                rows.append(
                    {
                        **identity,
                        "development_method": development_method,
                        "tail_method": tail_method,
                        "tail_factor": factor,
                        "status": status,
                        "warning_message": warning,
                        "curve_slope": slope,
                        "curve_intercept": intercept,
                        "bondy_exponent": exponent,
                    }
                )

    columns = TAIL_GROUP + [
        "tail_method",
        "tail_factor",
        "status",
        "warning_message",
        "curve_slope",
        "curve_intercept",
        "bondy_exponent",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        TAIL_GROUP + ["tail_method"]
    ).reset_index(drop=True)


def _match_identity(frame: pd.DataFrame, identity: dict[str, object]) -> pd.DataFrame:
    match = pd.Series(True, index=frame.index)
    for column, value in identity.items():
        match &= frame[column] == value
    return frame.loc[match]
