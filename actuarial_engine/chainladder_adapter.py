"""Thin integration boundary around the official chainladder package."""

from __future__ import annotations

from dataclasses import dataclass

import chainladder as cl
import numpy as np
import pandas as pd

from .config import EngineConfig, GRAIN_STEPS


@dataclass(frozen=True)
class PatternFit:
    triangle: cl.Triangle
    developed: cl.Triangle
    complete_pattern: cl.Triangle
    development_estimator: cl.Development
    tail_estimator: object | None
    tail_factor: float


def build_triangle(frame: pd.DataFrame) -> cl.Triangle:
    """Build one chainladder Triangle from one pool/grain/measure frame."""

    data = frame[
        ["accident_period", "valuation_date", "cumulative_value"]
    ].copy()
    data["accident_period"] = pd.to_datetime(data["accident_period"])
    data["valuation_date"] = pd.to_datetime(data["valuation_date"])
    return cl.Triangle(
        data=data,
        origin="accident_period",
        development="valuation_date",
        columns="cumulative_value",
        cumulative=True,
    )


def fit_development(
    triangle: cl.Triangle,
    method: str,
    config: EngineConfig,
) -> tuple[cl.Development, cl.Triangle]:
    """Fit a package Development estimator for one configured method."""

    parameters = {
        "simple_average": {"average": "simple", "n_periods": -1},
        "volume_weighted": {"average": "volume", "n_periods": -1},
        "recent_3_weighted": {
            "average": "volume",
            "n_periods": config.recent_period_count,
        },
        "regression": {"average": "regression", "n_periods": -1},
    }
    if method not in parameters:
        raise ValueError(f"Unsupported development method: {method}")
    estimator = cl.Development(**parameters[method])
    return estimator, estimator.fit_transform(triangle)


def fit_tail(
    developed: cl.Triangle,
    method: str,
    config: EngineConfig,
) -> tuple[object | None, cl.Triangle, float]:
    """Apply one chainladder tail transformer and return its point estimate."""

    if method == "none":
        return None, developed, 1.0

    projection_period = _projection_months(developed, config)
    if method == "constant":
        estimator = cl.TailConstant(
            tail=config.constant_tail_factor,
            projection_period=projection_period,
        )
    elif method == "curve":
        estimator = cl.TailCurve(
            curve="exponential",
            extrap_periods=config.tail_projection_periods,
            fit_period=_curve_fit_period(developed, config),
            errors="raise",
            projection_period=projection_period,
        )
    elif method == "bondy":
        estimator = cl.TailBondy(
            earliest_age=config.bondy_earliest_age,
            projection_period=projection_period,
        )
    else:
        raise ValueError(f"Unsupported tail method: {method}")

    complete = estimator.fit_transform(developed)
    tail_factor = scalar_from_values(estimator.tail_.values)
    return estimator, complete, tail_factor


def fit_pattern(
    triangle: cl.Triangle,
    development_method: str,
    tail_method: str,
    config: EngineConfig,
) -> PatternFit:
    development_estimator, developed = fit_development(
        triangle, development_method, config
    )
    tail_estimator, complete, tail_factor = fit_tail(developed, tail_method, config)
    return PatternFit(
        triangle=triangle,
        developed=developed,
        complete_pattern=complete,
        development_estimator=development_estimator,
        tail_estimator=tail_estimator,
        tail_factor=tail_factor,
    )


def triangle_origins(triangle: cl.Triangle) -> list[pd.Timestamp]:
    """Return package origins as normalized timestamps in package order."""

    # origins: accident periods
    # chainladder could change annual origin to pandas Period
    # Period("2022", freq="Y-DEC")
    origins: list[pd.Timestamp] = []
    for origin in triangle.origin:
        value = origin.start_time if hasattr(origin, "start_time") else origin

        # .normalize() set time to midnight
        origins.append(pd.Timestamp(value).normalize())
    return origins


def triangle_vector(triangle: cl.Triangle) -> dict[pd.Timestamp, float]:
    """Map a one-column, one-development Triangle result by origin."""
    # 作用是將「每個 accident period 只有一個結果」的 Triangle 轉成 dictionary。
    # 這個 function 只適用於「一個 value 對應一個 origin」的結果，例如：
    # ultimate_, ibnr_, latest_diagonal, Cape Cod apriori_

    values = np.asarray(triangle.values, dtype=float).reshape(-1)
    origins = triangle_origins(triangle)
    if len(values) != len(origins):
        raise ValueError(
            f"Expected one value per origin, received {len(values)} values for "
            f"{len(origins)} origins"
        )
    return dict(zip(origins, values, strict=True))


def make_sample_weight(
    triangle: cl.Triangle,
    values_by_origin: dict[pd.Timestamp, float],
) -> cl.Triangle:
    """Create the package's required latest-diagonal sample-weight Triangle."""
    # BF、Cape Cod、Benktander 和 Expected Loss 需要額外的 expected loss 或 exposure
    # 而且輸入必須是和 triangle 相容的 sample_weight Triangle

    weight = triangle.latest_diagonal * 0.0
    values = np.asarray(weight.values, dtype=float).copy()
    origins = triangle_origins(weight)
    values[0, 0, :, 0] = [values_by_origin.get(origin, np.nan) for origin in origins]
    weight.values = values
    return weight


def selected_ldf_values(
    developed: cl.Triangle,
    source_triangle: cl.Triangle,
) -> list[tuple[int, int, float]]:
    """Extract package-selected LDFs with numeric from/to development ages."""

    ages = [int(age) for age in source_triangle.development]
    values = np.asarray(developed.ldf_.values, dtype=float).reshape(-1)
    return [
        (ages[index], ages[index + 1], float(value))
        for index, value in enumerate(values[: max(len(ages) - 1, 0)])
    ]


def tail_diagnostics(estimator: object | None) -> tuple[float, float, float]:
    """Extract package-fitted curve or Bondy diagnostics when available."""
    # TailCurve → slope_、intercept_ e.g. (-0.42, 0.15, nan)
    # TailBondy → b_ e.g. (nan, nan, 0.50)
    # TailConstant → 通常沒有這三個 attributes e.g. (nan, nan, nan)

    nan = float("nan")
    if estimator is None:
        return nan, nan, nan
    slope = _optional_scalar(estimator, "slope_")
    intercept = _optional_scalar(estimator, "intercept_")
    exponent = _optional_scalar(estimator, "b_")
    return slope, intercept, exponent


def scalar_from_values(values: object) -> float:
    # 把 package 可能回傳的 scalar、list 或多維 array 統一轉成一個 float
    # 只保留不是以下類型的值： NaN, positive infinity, negative infinity

    array = np.asarray(values, dtype=float).reshape(-1)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return float("nan")
    return float(finite[-1])


def _optional_scalar(estimator: object, attribute: str) -> float:
    # _optional_scalar(estimator, "slope_")
    # estimator.slope_
    # 如果 slope_ 不存在，不會產生 AttributeError，而是回傳 NaN

    value = getattr(estimator, attribute, None)
    if value is None:
        return float("nan")
    values = value.values if hasattr(value, "values") else value
    return scalar_from_values(values)


def _curve_fit_period(
    developed: cl.Triangle,
    config: EngineConfig,
) -> tuple[int | None, None]:
    # 告訴 TailCurve 使用最後幾個 LDF 來 fit tail curve
    # ages = [12, 24, 36, 48, 60, 72]
    # ldf_count = 5
    # tail_curve_fit_periods = 3
    # start_index = 5 - 3 = 2
    # start_age = ages[2] = 36
    # return (36, None)

    ages = [int(age) for age in developed.development]
    ldf_count = max(len(ages) - 1, 0)
    if ldf_count <= config.tail_curve_fit_periods:
        return None, None
    return ages[ldf_count - config.tail_curve_fit_periods], None


def _projection_months(developed: cl.Triangle, config: EngineConfig) -> int:
    # 決定 tail 要向後延伸多少月份
    # 最小12個月
    
    grain_code = str(developed.development_grain).upper()
    step_by_code = {"M": 1, "Q": 3, "S": 6, "Y": 12}
    step = step_by_code.get(grain_code)
    if step is None:
        ages = [int(age) for age in developed.development]
        step = ages[1] - ages[0] if len(ages) > 1 else GRAIN_STEPS["annual"]
    return max(step * config.tail_projection_periods, 12)
