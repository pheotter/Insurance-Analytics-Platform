"""Configuration and method registry for the actuarial engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


GRAIN_STEPS = {
    "monthly": 1,
    "quarterly": 3,
    "half_year": 6,
    "annual": 12,
}

MEASURE_COLUMNS = {
    "paid": "cumulative_paid_loss",
    "paid_and_expense": "cumulative_paid_and_expense",
    "incurred": "cumulative_incurred_loss",
    "reported_count": "cumulative_reported_claim_count",
}

DEVELOPMENT_METHODS = (
    "simple_average",
    "volume_weighted",
    "recent_3_weighted",
    "regression",
)

TAIL_METHODS = ("none", "constant", "curve", "bondy")

ULTIMATE_METHODS = (
    "chainladder",
    "mack_chainladder",
    "bornhuetter_ferguson",
    "cape_cod",
    "benktander",
    "expected_loss",
)

METHOD_REQUIREMENTS = {
    "chainladder": frozenset({"triangle"}),
    "mack_chainladder": frozenset({"triangle", "mack_variance"}),
    "bornhuetter_ferguson": frozenset({"triangle", "expected_value"}),
    "cape_cod": frozenset({"triangle", "exposure_base"}),
    "benktander": frozenset({"triangle", "expected_value"}),
    "expected_loss": frozenset({"expected_value"}),
}


@dataclass(frozen=True)
class EngineConfig:
    """Run-level calculation choices.

    Defaults intentionally constrain the first production workflow to annual
    incurred triangles while retaining all methods as supported interfaces.
    """

    as_of_date: date
    triangle_grains: tuple[str, ...] = ("annual",)
    measures: tuple[str, ...] = ("incurred",)
    development_methods: tuple[str, ...] = (
        "simple_average",
        "volume_weighted",
        "recent_3_weighted",
    )
    tail_methods: tuple[str, ...] = ("none", "curve")
    ultimate_methods: tuple[str, ...] = (
        "chainladder",
        "mack_chainladder",
        "bornhuetter_ferguson",
        "cape_cod",
    )
    recent_period_count: int = 3
    minimum_regression_observations: int = 2
    tail_curve_fit_periods: int = 5
    tail_projection_periods: int = 10
    constant_tail_factor: float = 1.0
    bondy_earliest_age: int | None = None
    benktander_iterations: int = 2
    engine_name: str = "actuarial_engine"
    engine_version: str = "0.1.0"

    def __post_init__(self) -> None:
        _validate_choices("triangle_grains", self.triangle_grains, GRAIN_STEPS)
        _validate_choices("measures", self.measures, MEASURE_COLUMNS)
        _validate_choices(
            "development_methods", self.development_methods, DEVELOPMENT_METHODS
        )
        _validate_choices("tail_methods", self.tail_methods, TAIL_METHODS)
        _validate_choices("ultimate_methods", self.ultimate_methods, ULTIMATE_METHODS)

        if self.recent_period_count < 1:
            raise ValueError("recent_period_count must be at least 1")
        if self.minimum_regression_observations < 2:
            raise ValueError("minimum_regression_observations must be at least 2")
        if self.tail_curve_fit_periods < 2:
            raise ValueError("tail_curve_fit_periods must be at least 2")
        if self.tail_projection_periods < 1:
            raise ValueError("tail_projection_periods must be at least 1")
        if self.constant_tail_factor < 1.0:
            raise ValueError("constant_tail_factor cannot be below 1.0")
        if self.bondy_earliest_age is not None and self.bondy_earliest_age < 0:
            raise ValueError("bondy_earliest_age cannot be negative")
        if self.benktander_iterations < 1:
            raise ValueError("benktander_iterations must be at least 1")


def _validate_choices(
    field_name: str,
    selected: tuple[str, ...],
    supported: object,
) -> None:
    supported_values = set(supported)
    unknown = sorted(set(selected) - supported_values)
    if unknown:
        raise ValueError(f"Unsupported {field_name}: {', '.join(unknown)}")
    if not selected:
        raise ValueError(f"{field_name} cannot be empty")
