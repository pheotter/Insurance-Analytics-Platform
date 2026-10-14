"""Package-backed deterministic and stochastic ultimate candidates."""

from __future__ import annotations

import math

import chainladder as cl
import numpy as np
import pandas as pd

from .chainladder_adapter import (
    build_triangle,
    fit_pattern,
    make_sample_weight,
    triangle_origins,
    triangle_vector,
)
from .config import EngineConfig
from .development import DEVELOPMENT_GROUP
from .validation import normalize_columns


PATTERN_GROUP = DEVELOPMENT_GROUP + ["development_method", "tail_method"]


def calculate_model_candidates(
    triangle: pd.DataFrame,
    latest: pd.DataFrame,
    ldf_candidates: pd.DataFrame,
    tail_candidates: pd.DataFrame,
    expected_input: pd.DataFrame | None,
    config: EngineConfig,
) -> pd.DataFrame:
    """Run configured chainladder estimators for each complete pattern."""

    expected = _prepare_expected_input(expected_input)
    rows: list[dict[str, object]] = []

    for key, group in triangle.groupby(DEVELOPMENT_GROUP, dropna=False):
        identity = dict(zip(DEVELOPMENT_GROUP, key, strict=True))
        package_triangle = build_triangle(group)
        latest_group = _match_identity(latest, identity)
        pool_tails = _match_identity(tail_candidates, identity)
        pool_ldfs = _match_identity(ldf_candidates, identity)

        for development_method in config.development_methods:
            method_ldfs = pool_ldfs.loc[
                pool_ldfs["development_method"] == development_method
            ]
            for tail_method in config.tail_methods:
                tail_row = pool_tails.loc[
                    (pool_tails["development_method"] == development_method)
                    & (pool_tails["tail_method"] == tail_method)
                ]
                pattern_identity = {
                    **identity,
                    "development_method": development_method,
                    "tail_method": tail_method,
                }
                if (
                    tail_row.empty
                    or tail_row.iloc[0]["status"] != "AVAILABLE"
                    or method_ldfs.empty
                    or (method_ldfs["status"] != "AVAILABLE").any()
                ):
                    warning = (
                        tail_row.iloc[0]["warning_message"]
                        if not tail_row.empty
                        else "TAIL_CANDIDATE_NOT_FOUND"
                    )
                    rows.extend(
                        _unavailable_rows(
                            latest_group,
                            pattern_identity,
                            config.ultimate_methods,
                            warning or "INCOMPLETE_DEVELOPMENT_PATTERN",
                        )
                    )
                    continue

                try:
                    pattern = fit_pattern(
                        package_triangle,
                        development_method,
                        tail_method,
                        config,
                    )
                    chainladder_model = cl.Chainladder().fit(
                        pattern.complete_pattern
                    )
                    latest_values = triangle_vector(
                        pattern.complete_pattern.latest_diagonal
                    )
                    chainladder_ultimates = triangle_vector(
                        chainladder_model.ultimate_
                    )
                except Exception as exception:
                    rows.extend(
                        _unavailable_rows(
                            latest_group,
                            pattern_identity,
                            config.ultimate_methods,
                            f"CHAINLADDER_PATTERN_ERROR: {exception}",
                        )
                    )
                    continue

                origins = triangle_origins(pattern.complete_pattern)
                expected_values = _input_values_by_origin(
                    expected, identity, origins
                )
                cdf_by_origin = {
                    origin: (
                        chainladder_ultimates[origin] / latest_values[origin]
                        if latest_values[origin] > 0
                        else math.nan
                    )
                    for origin in origins
                }

                for ultimate_method in config.ultimate_methods:
                    rows.extend(
                        _fit_ultimate_method(
                            pattern.complete_pattern,
                            latest_group,
                            pattern_identity,
                            ultimate_method,
                            expected_values,
                            cdf_by_origin,
                            config,
                        )
                    )

    columns = PATTERN_GROUP + [
        "accident_period",
        "latest_observed_value",
        "latest_development_age",
        "cdf",
        "percent_developed",
        "ultimate_method",
        "exposure_base",
        "expected_loss_ratio",
        "expected_value",
        "ultimate_value",
        "ibnr_value",
        "mack_standard_error",
        "status",
        "warning_message",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        PATTERN_GROUP + ["ultimate_method", "accident_period"]
    ).reset_index(drop=True)


def _fit_ultimate_method(
    pattern: cl.Triangle,
    latest: pd.DataFrame,
    identity: dict[str, object],
    method: str,
    inputs: dict[str, dict[pd.Timestamp, float]],
    cdf_by_origin: dict[pd.Timestamp, float],
    config: EngineConfig,
) -> list[dict[str, object]]:
    origins = triangle_origins(pattern)
    missing_reason = _missing_input_reason(method, origins, inputs)
    if method == "mack_chainladder" and identity["development_method"] != "volume_weighted":
        missing_reason = "MACK_REQUIRES_VOLUME_WEIGHTED_DEVELOPMENT"
    if missing_reason:
        return _unavailable_rows(
            latest, identity, (method,), missing_reason, cdf_by_origin
        )

    try:
        if method == "chainladder":
            estimator = cl.Chainladder().fit(pattern)
        elif method == "mack_chainladder":
            estimator = cl.MackChainladder().fit(pattern)
        elif method == "bornhuetter_ferguson":
            estimator = cl.BornhuetterFerguson(apriori=1.0).fit(
                pattern,
                sample_weight=make_sample_weight(pattern, inputs["expected_value"]),
            )
        elif method == "cape_cod":
            estimator = cl.CapeCod().fit(
                pattern,
                sample_weight=make_sample_weight(pattern, inputs["exposure_base"]),
            )
        elif method == "benktander":
            estimator = cl.Benktander(
                apriori=1.0, n_iters=config.benktander_iterations
            ).fit(
                pattern,
                sample_weight=make_sample_weight(pattern, inputs["expected_value"]),
            )
        elif method == "expected_loss":
            estimator = cl.ExpectedLoss(apriori=1.0).fit(
                pattern,
                sample_weight=make_sample_weight(pattern, inputs["expected_value"]),
            )
        else:
            raise ValueError(f"Unsupported ultimate method: {method}")
    except Exception as exception:
        return _unavailable_rows(
            latest,
            identity,
            (method,),
            f"CHAINLADDER_{method.upper()}_ERROR: {exception}",
            cdf_by_origin,
        )

    ultimate = triangle_vector(estimator.ultimate_)
    ibnr = triangle_vector(estimator.ibnr_)
    mack_error = (
        _last_development_vector(estimator.mack_std_err_)
        if method == "mack_chainladder"
        else {}
    )
    cape_cod_ratio = (
        triangle_vector(estimator.apriori_) if method == "cape_cod" else {}
    )
    latest_lookup = {
        pd.Timestamp(row.accident_period).normalize(): row
        for row in latest.itertuples()
    }

    rows: list[dict[str, object]] = []
    for origin in origins:
        latest_row = latest_lookup[origin]
        standard_error = mack_error.get(origin, math.nan)
        status = "AVAILABLE"
        warning = None
        if method == "mack_chainladder" and not np.isfinite(standard_error):
            status = "AVAILABLE_WITH_WARNING"
            warning = "CHAINLADDER_MACK_STANDARD_ERROR_NOT_ESTIMABLE"
        if method == "mack_chainladder" and identity["tail_method"] != "none":
            status = "AVAILABLE_WITH_WARNING"
            warning = "MACK_STANDARD_ERROR_TAIL_TREATMENT_IS_PACKAGE_DEFINED"

        expected_ratio = inputs["expected_loss_ratio"].get(origin, math.nan)
        if method == "cape_cod":
            expected_ratio = cape_cod_ratio.get(origin, math.nan)
        rows.append(
            {
                **identity,
                "accident_period": origin,
                "latest_observed_value": float(latest_row.latest_observed_value),
                "latest_development_age": int(latest_row.latest_development_age),
                "cdf": cdf_by_origin.get(origin, math.nan),
                "percent_developed": (
                    1.0 / cdf_by_origin[origin]
                    if cdf_by_origin.get(origin, 0) > 0
                    else math.nan
                ),
                "ultimate_method": method,
                "exposure_base": inputs["exposure_base"].get(origin, math.nan),
                "expected_loss_ratio": expected_ratio,
                "expected_value": inputs["expected_value"].get(origin, math.nan),
                "ultimate_value": ultimate.get(origin, math.nan),
                "ibnr_value": ibnr.get(origin, math.nan),
                "mack_standard_error": standard_error,
                "status": status,
                "warning_message": warning,
            }
        )
    return rows


def _prepare_expected_input(expected_input: pd.DataFrame | None) -> pd.DataFrame:
    if expected_input is None or expected_input.empty:
        return pd.DataFrame()
    frame = normalize_columns(expected_input)
    frame["accident_period"] = pd.to_datetime(frame["accident_period"]).dt.normalize()
    if "exposure_base" not in frame.columns:
        if "earned_premium" in frame.columns:
            frame["exposure_base"] = frame["earned_premium"]
        elif "earned_exposure" in frame.columns:
            frame["exposure_base"] = frame["earned_exposure"]
    if "expected_value" not in frame.columns and "expected_loss" in frame.columns:
        frame["expected_value"] = frame["expected_loss"]
    if (
        "expected_value" not in frame.columns
        and "exposure_base" in frame.columns
        and "expected_loss_ratio" in frame.columns
    ):
        frame["expected_value"] = (
            pd.to_numeric(frame["exposure_base"], errors="coerce")
            * pd.to_numeric(frame["expected_loss_ratio"], errors="coerce")
        )
    return frame


def _input_values_by_origin(
    expected: pd.DataFrame,
    identity: dict[str, object],
    origins: list[pd.Timestamp],
) -> dict[str, dict[pd.Timestamp, float]]:
    output = {
        "exposure_base": {},
        "expected_loss_ratio": {},
        "expected_value": {},
    }
    if expected.empty:
        return output

    matching = expected.loc[
        expected["development_pool_id"] == identity["development_pool_id"]
    ]
    if "triangle_grain" in matching.columns:
        matching = matching.loc[
            matching["triangle_grain"] == identity["triangle_grain"]
        ]
    if "measure_type" in matching.columns:
        matching = matching.loc[
            matching["measure_type"] == identity["measure_type"]
        ]
    records = {
        pd.Timestamp(row.accident_period).normalize(): row
        for row in matching.itertuples()
    }
    for origin in origins:
        record = records.get(origin)
        if record is None:
            continue
        for column in output:
            value = getattr(record, column, math.nan)
            output[column][origin] = float(value) if pd.notna(value) else math.nan
    return output


def _missing_input_reason(
    method: str,
    origins: list[pd.Timestamp],
    inputs: dict[str, dict[pd.Timestamp, float]],
) -> str | None:
    if method in {"bornhuetter_ferguson", "benktander", "expected_loss"}:
        values = inputs["expected_value"]
        if any(not np.isfinite(values.get(origin, math.nan)) for origin in origins):
            return "MISSING_EXPECTED_VALUE"
    if method == "cape_cod":
        values = inputs["exposure_base"]
        if any(
            not np.isfinite(values.get(origin, math.nan))
            or values.get(origin, math.nan) <= 0
            for origin in origins
        ):
            return "MISSING_EXPOSURE_BASE"
    return None


def _unavailable_rows(
    latest: pd.DataFrame,
    identity: dict[str, object],
    methods: tuple[str, ...],
    warning: str,
    cdf_by_origin: dict[pd.Timestamp, float] | None = None,
) -> list[dict[str, object]]:
    cdf_by_origin = cdf_by_origin or {}
    rows: list[dict[str, object]] = []
    for latest_row in latest.itertuples():
        origin = pd.Timestamp(latest_row.accident_period).normalize()
        cdf = cdf_by_origin.get(origin, math.nan)
        for method in methods:
            rows.append(
                {
                    **identity,
                    "accident_period": origin,
                    "latest_observed_value": float(latest_row.latest_observed_value),
                    "latest_development_age": int(latest_row.latest_development_age),
                    "cdf": cdf,
                    "percent_developed": 1.0 / cdf if cdf > 0 else math.nan,
                    "ultimate_method": method,
                    "exposure_base": math.nan,
                    "expected_loss_ratio": math.nan,
                    "expected_value": math.nan,
                    "ultimate_value": math.nan,
                    "ibnr_value": math.nan,
                    "mack_standard_error": math.nan,
                    "status": "NOT_AVAILABLE",
                    "warning_message": warning,
                }
            )
    return rows


def _last_development_vector(triangle: cl.Triangle) -> dict[pd.Timestamp, float]:
    values = np.asarray(triangle.values, dtype=float)[0, 0, :, -1]
    origins = triangle_origins(triangle)
    return dict(zip(origins, values, strict=True))


def _match_identity(frame: pd.DataFrame, identity: dict[str, object]) -> pd.DataFrame:
    match = pd.Series(True, index=frame.index)
    for column, value in identity.items():
        match &= frame[column] == value
    return frame.loc[match]
