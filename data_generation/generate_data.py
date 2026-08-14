"""Generate synthetic multi-line insurance operational source data.

Common transaction schemas are shared across lines of business. Risk,
coverage-selection, pricing, and claim-severity logic stays LOB-specific so
each insurance product can evolve without creating one monster generator.
"""

from __future__ import annotations

import argparse
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas
import snowflake.connector

load_dotenv()

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

N_AUTO_POLICIES = 50_000
N_PROPERTY_POLICIES = 20_000
START_DATE = datetime(2019, 1, 1)
END_DATE = datetime(2023, 12, 31)

PRODUCT_CONFIG = {
    "personal_auto": {
        "product_id": "pa_standard",
        "policy_prefix": "PA",
        "source_system": "policy_admin_auto_sim",
        "claim_source_system": "claims_admin_auto_sim",
        "term_months": [6, 12],
        "term_weights": [0.65, 0.35],
    },
    "commercial_property": {
        "product_id": "cp_standard",
        "policy_prefix": "CP",
        "source_system": "policy_admin_property_sim",
        "claim_source_system": "claims_admin_property_sim",
        "term_months": [6, 12],
        "term_weights": [0.05, 0.95],
    },
}

STATES = ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI"]

UNDERWRITING_TIERS = {
    "preferred": {"weight": 0.30, "frequency_multiplier": 0.70, "premium_multiplier": 0.85},
    "standard": {"weight": 0.45, "frequency_multiplier": 1.00, "premium_multiplier": 1.00},
    "nonstandard": {"weight": 0.20, "frequency_multiplier": 1.45, "premium_multiplier": 1.25},
    "high_risk": {"weight": 0.05, "frequency_multiplier": 1.75, "premium_multiplier": 1.70},
}

VEHICLE_PROFILES = {
    "sedan": {
        "make_models": [("Toyota", "Camry"), ("Honda", "Civic")],
        "pricing_factor": 1.00,
        "true_risk_factor": 1.00,
    },
    "suv": {
        "make_models": [("Toyota", "RAV4"), ("Ford", "Escape")],
        "pricing_factor": 1.15,
        "true_risk_factor": 1.05,
    },
    "truck": {
        "make_models": [("Ford", "F-150"), ("Chevrolet", "Silverado")],
        "pricing_factor": 1.20,
        "true_risk_factor": 1.10,
    },
    "sports": {
        "make_models": [("Ford", "Mustang"), ("Chevrolet", "Camaro")],
        "pricing_factor": 1.45,
        "true_risk_factor": 1.25,
    },
}

AUTO_COVERAGES = {
    "AUTO_BI": {
        "coverage_family": "bodily_injury",
        "limit": 100_000,
        "deductible": 0,
        "base_rate": 420,
        "selection_probability": 1.00,
    },
    "AUTO_PD": {
        "coverage_family": "property_damage_liability",
        "limit": 50_000,
        "deductible": 0,
        "base_rate": 180,
        "selection_probability": 1.00,
    },
    "AUTO_COLL": {
        "coverage_family": "collision",
        "limit": 50_000,
        "deductible": 500,
        "base_rate": 310,
        "selection_probability": 0.65,
    },
    "AUTO_COMP": {
        "coverage_family": "comprehensive",
        "limit": 50_000,
        "deductible": 500,
        "base_rate": 170,
        "selection_probability": 0.75,
    },
}

AUTO_SEVERITY_TREND = 0.06
AUTO_PREMIUM_TREND = 0.04
PROPERTY_SEVERITY_TREND = 0.05
PROPERTY_PREMIUM_TREND = 0.035

AUTO_DEDUCTIBLE_TABLE = {
    0: 1.00,
    250: 0.95,
    500: 0.90,
    1000: 0.80,
    2500: 0.65,
}

AUTO_LIMIT_TABLE = {
    25000: 0.85,
    50000: 1.00,
    100000: 1.25,
    250000: 1.60,
    500000: 2.10,
}

PROPERTY_OCCUPANCIES = {
    "office": {
        "weight": 0.30,
        "frequency_factor": 0.80,
        "severity_factor": 0.90,
        "premium_factor": 0.90,
    },
    "retail": {
        "weight": 0.25,
        "frequency_factor": 1.00,
        "severity_factor": 1.00,
        "premium_factor": 1.00,
    },
    "warehouse": {
        "weight": 0.25,
        "frequency_factor": 1.15,
        "severity_factor": 1.20,
        "premium_factor": 1.10,
    },
    "manufacturing": {
        "weight": 0.20,
        "frequency_factor": 1.35,
        "severity_factor": 1.40,
        "premium_factor": 1.25,
    },
}

PROPERTY_CONSTRUCTIONS = {
    "frame": {"weight": 0.30, "frequency_factor": 1.20, "premium_factor": 1.15},
    "masonry": {"weight": 0.35, "frequency_factor": 1.00, "premium_factor": 1.00},
    "noncombustible": {"weight": 0.20, "frequency_factor": 0.85, "premium_factor": 0.90},
    "fire_resistive": {"weight": 0.15, "frequency_factor": 0.70, "premium_factor": 0.80},
}

PROPERTY_COVERAGES = {
    "BUILDING": {
        "coverage_family": "building",
        "selection_probability": 1.00,
        "limit_factor": 1.00,
        "deductible": 10_000,
        "base_rate": 0.0025,
    },
    "BUSINESS_PERSONAL_PROPERTY": {
        "coverage_family": "business_personal_property",
        "selection_probability": 0.75,
        "limit_factor": 0.75,
        "deductible": 5_000,
        "base_rate": 0.0018,
    },
}

PROPERTY_PRICING_FACTORS = {
    "state": {"FL": 1.10, "TX": 1.05, "GA": 1.03},
    "protection_class": 1.00,
}

PROPERTY_TRUE_RISK_FACTORS = {
    "state": {"FL": 1.30, "TX": 1.15, "GA": 1.10},
    "protection_class": {1: 0.85, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05,
                         6: 1.10, 7: 1.15, 8: 1.20, 9: 1.25, 10: 1.30},
}

AUTO_CLAIM_SCENARIOS = [
    {
        "claim_type": "collision",
        "cause_code": "at_fault",
        "coverage_code": "AUTO_COLL",
        "weight": 0.42,
        "severity": 7_500,
        "recovery_ratio": 0.00,
    },
    {
        "claim_type": "weather",
        "cause_code": "weather",
        "coverage_code": "AUTO_COMP",
        "weight": 0.20,
        "severity": 5_500,
        "recovery_ratio": 0.05,
    },
    {
        "claim_type": "theft",
        "cause_code": "theft",
        "coverage_code": "AUTO_COMP",
        "weight": 0.08,
        "severity": 6_000,
        "recovery_ratio": 0.05,
    },
    {
        "claim_type": "bodily_injury",
        "cause_code": "at_fault",
        "coverage_code": "AUTO_BI",
        "weight": 0.17,
        "severity": 12_000,
        "recovery_ratio": 0.00,
    },
    {
        "claim_type": "property_damage",
        "cause_code": "at_fault",
        "coverage_code": "AUTO_PD",
        "weight": 0.13,
        "severity": 6_000,
        "recovery_ratio": 0.00,
    },
]

PROPERTY_CLAIM_SCENARIOS = [
    {
        "claim_type": "fire",
        "cause_code": "fire",
        "coverage_code": "BUILDING",
        "weight": 0.15,
        "damage_alpha": 1.5,
        "damage_beta": 8.0,
        "recovery_ratio": 0.03,
    },
    {
        "claim_type": "wind_hail",
        "cause_code": "weather",
        "coverage_code": "BUILDING",
        "weight": 0.35,
        "damage_alpha": 1.5,
        "damage_beta": 18.0,
        "recovery_ratio": 0.02,
    },
    {
        "claim_type": "water",
        "cause_code": "water",
        "coverage_code": "BUSINESS_PERSONAL_PROPERTY",
        "weight": 0.30,
        "damage_alpha": 1.4,
        "damage_beta": 12.0,
        "recovery_ratio": 0.03,
    },
    {
        "claim_type": "theft",
        "cause_code": "theft",
        "coverage_code": "BUSINESS_PERSONAL_PROPERTY",
        "weight": 0.20,
        "damage_alpha": 1.2,
        "damage_beta": 20.0,
        "recovery_ratio": 0.10,
    },
]

AUTO_PAYMENT_PATTERN = [0.00, 0.20, 0.50, 0.80, 1.00]
AUTO_RESERVE_PATTERN = [0.85, 0.65, 0.35, 0.20, 0.00]
AUTO_DEVELOPMENT_MONTHS = [0, 1, 3, 6, 12]

PROPERTY_PAYMENT_PATTERN = [0.00, 0.10, 0.30, 0.65, 1.00]
PROPERTY_RESERVE_PATTERN = [0.90, 0.85, 0.65, 0.35, 0.00]
PROPERTY_DEVELOPMENT_MONTHS = [0, 3, 6, 12, 24]

POLICY_COLUMNS = [
    "POLICY_ID",
    "POLICY_NUMBER",
    "INSURED_ID",
    "PRODUCT_ID",
    "LINE_OF_BUSINESS",
    "EFFECTIVE_DATE",
    "EXPIRATION_DATE",
    "CANCELLATION_DATE",
    "STATUS",
    "UNDERWRITING_TIER",
    "PRIMARY_STATE",
    "TERM_MONTHS",
    "SOURCE_SYSTEM",
]

VEHICLE_COLUMNS = [
    "VEHICLE_ID", "POLICY_ID", "VEHICLE_SEQUENCE", "MODEL_YEAR",
    "MAKE", "MODEL", "VEHICLE_TYPE", "GARAGING_STATE",
    "ANNUAL_MILEAGE", "USAGE", "SAFETY_DEVICE_FLAG", "SOURCE_SYSTEM",
]

DRIVER_COLUMNS = [
    "DRIVER_ID", "POLICY_ID", "DRIVER_SEQUENCE", "DATE_OF_BIRTH",
    "GENDER", "YEARS_LICENSED", "PRIOR_ACCIDENTS", "PRIOR_VIOLATIONS",
    "MARITAL_STATUS", "CREDIT_TIER", "SOURCE_SYSTEM",
]

ASSIGNMENT_COLUMNS = [
    "ASSIGNMENT_ID", "POLICY_ID", "DRIVER_ID", "VEHICLE_ID",
    "ASSIGNMENT_TYPE", "EFFECTIVE_DATE", "EXPIRATION_DATE", "SOURCE_SYSTEM",
]

PROPERTY_LOCATION_COLUMNS = [
    "LOCATION_ID", "POLICY_ID", "LOCATION_SEQUENCE", "STATE", "ZIP_CODE",
    "OCCUPANCY", "CONSTRUCTION_TYPE", "YEAR_BUILT", "PROTECTION_CLASS",
    "TOTAL_INSURED_VALUE", "SOURCE_SYSTEM",
]

RISK_UNIT_COLUMNS = [
    "RISK_UNIT_ID",
    "POLICY_ID",
    "RISK_UNIT_TYPE",
    "SOURCE_RISK_UNIT_ID",
    "EFFECTIVE_DATE",
    "EXPIRATION_DATE",
    "STATUS",
    "EXPOSURE_UNIT",
    "SOURCE_SYSTEM",
]

COVERAGE_COLUMNS = [
    "COVERAGE_ID",
    "POLICY_ID",
    "RISK_UNIT_ID",
    "COVERAGE_CODE",
    "COVERAGE_FAMILY",
    "EFFECTIVE_DATE",
    "EXPIRATION_DATE",
    "LIMIT_AMOUNT",
    "DEDUCTIBLE_AMOUNT",
    "WRITTEN_PREMIUM",
    "SOURCE_SYSTEM",
]

CLAIM_COLUMNS = [
    "CLAIM_ID",
    "POLICY_ID",
    "RISK_UNIT_ID",
    "COVERAGE_ID",
    "COVERAGE_CODE",
    "LOSS_DATE",
    "REPORTED_DATE",
    "CLAIM_TYPE",
    "CAUSE_CODE",
    "CLAIM_STATUS",
    "SOURCE_SYSTEM",
]

PREMIUM_TRANSACTION_COLUMNS = [
    "TRANSACTION_ID",
    "POLICY_ID",
    "COVERAGE_ID",
    "TRANSACTION_TYPE",
    "TRANSACTION_DATE",
    "TRANSACTION_REASON",
    "PREMIUM_CHANGE",
    "CUMULATIVE_PREMIUM",
    "SOURCE_SYSTEM",
]

CLAIM_TRANSACTION_COLUMNS = [
    "TRANSACTION_ID",
    "CLAIM_ID",
    "TRANSACTION_TYPE",
    "TRANSACTION_DATE",
    "PAID_LOSS_CHANGE",
    "CASE_RESERVE_CHANGE",
    "PAID_EXPENSE_CHANGE",
    "CASE_EXPENSE_CHANGE",
    "RECOVERY_CHANGE",
    "INCURRED_LOSS_CHANGE",
    "SOURCE_SYSTEM",
]

RAW_TABLES = (
    "raw_policy",
    "raw_policy_risk_unit",
    "raw_policy_coverage",
    "raw_premium_transaction",
    "raw_claim",
    "raw_claim_transaction",
    "raw_vehicle",
    "raw_driver",
    "raw_driver_vehicle_assignment",
    "raw_property_location",
)


def rand_date(start: datetime, end: datetime) -> datetime:
    return start + timedelta(days=random.randint(0, max((end - start).days, 0)))


def weighted_choice(options: dict) -> str:
    keys = list(options)
    weights = [options[key]["weight"] for key in keys]
    return random.choices(keys, weights=weights, k=1)[0]


def actual_end_date(row: pd.Series | dict) -> datetime:
    expiration = pd.to_datetime(row["EXPIRATION_DATE"]).to_pydatetime()
    cancellation = row["CANCELLATION_DATE"]
    if pd.isna(cancellation):
        return expiration
    return min(expiration, pd.to_datetime(cancellation).to_pydatetime())


def coverage_term_factor(
    effective_date: object,
    expiration_date: object,
) -> float:
    """Return the Actual/365.25 portion of a year covered by the term."""
    effective = pd.to_datetime(effective_date).to_pydatetime()
    expiration = pd.to_datetime(expiration_date).to_pydatetime()
    coverage_days = (expiration - effective).days
    if coverage_days <= 0:
        raise ValueError("Coverage expiration date must be after effective date")
    return coverage_days / 365.25


def risk_exposure_window(
    policy: dict,
    risk_unit: dict,
) -> tuple[datetime, datetime, float]:
    effective_date = pd.to_datetime(
        risk_unit["EFFECTIVE_DATE"]
    ).to_pydatetime()
    policy_end = actual_end_date(policy)
    risk_expiration = pd.to_datetime(
        risk_unit["EXPIRATION_DATE"]
    ).to_pydatetime()
    risk_end = min(policy_end, risk_expiration, END_DATE)
    exposure_years = max(
        (risk_end - effective_date).days / 365.25,
        0.0,
    )
    return effective_date, risk_end, exposure_years


def severity_trend_factor(loss_date: datetime, annual_trend: float) -> float:
    years_since_start = max(loss_date.year - START_DATE.year, 0)
    return (1 + annual_trend) ** years_since_start


def concat_with_schema(
    frames: list[pd.DataFrame],
    columns: list[str],
) -> pd.DataFrame:
    non_empty = [frame for frame in frames if not frame.empty]

    # no data
    if not non_empty:
        return pd.DataFrame(columns=columns)
    return pd.concat(non_empty, ignore_index=True).reindex(columns=columns)


def add_load_metadata(
    raw_tables: dict[str, pd.DataFrame],
    load_batch_id: str,
    ingested_at: datetime,
) -> dict[str, pd.DataFrame]:
    """Attach run-level audit metadata to every raw output table."""
    ingested_timestamp = pd.Timestamp(ingested_at)
    for dataframe in raw_tables.values():
        dataframe["LOAD_BATCH_ID"] = load_batch_id
        dataframe["INGESTED_AT"] = ingested_timestamp
    return raw_tables


def generate_raw_policy(
    n_auto: int = N_AUTO_POLICIES,
    n_property: int = N_PROPERTY_POLICIES,
) -> pd.DataFrame:
    rows = []
    policy_counter = 1

    policy_specs = [
        ("personal_auto", n_auto),
        ("commercial_property", n_property),
    ]

    for lob, policy_count in policy_specs:
        config = PRODUCT_CONFIG[lob]
        for sequence in range(1, policy_count + 1):
            policy_id = f"POL{policy_counter:08d}"
            effective_date = rand_date(START_DATE, datetime(2023, 6, 30))
            term_months = random.choices(
                config["term_months"],
                weights=config["term_weights"],
                k=1,
            )[0]
            expiration_date = (
                pd.Timestamp(effective_date)
                + pd.DateOffset(months=term_months)
            ).to_pydatetime()
            cancellation_date = None
            status = "active"

            if random.random() < 0.08:
                cancellation_date = rand_date(effective_date, expiration_date)
                status = "cancelled"
            elif expiration_date <= END_DATE:
                status = "expired"

            rows.append(
                {
                    "POLICY_ID": policy_id,
                    "POLICY_NUMBER": (
                        f"{config['policy_prefix']}-"
                        f"{effective_date.year}-{sequence:08d}"
                    ),
                    "INSURED_ID": f"INS{policy_counter:08d}",
                    "PRODUCT_ID": config["product_id"],
                    "LINE_OF_BUSINESS": lob,
                    "EFFECTIVE_DATE": effective_date.date(),
                    "EXPIRATION_DATE": expiration_date.date(),
                    "CANCELLATION_DATE": (
                        cancellation_date.date() if cancellation_date else None
                    ),
                    "STATUS": status,
                    "UNDERWRITING_TIER": weighted_choice(UNDERWRITING_TIERS),
                    "PRIMARY_STATE": random.choice(STATES),
                    "TERM_MONTHS": term_months,
                    "SOURCE_SYSTEM": config["source_system"],
                }
            )
            policy_counter += 1

    return pd.DataFrame(rows, columns=POLICY_COLUMNS)


def generate_raw_vehicle(policies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    vehicle_counter = 1

    for policy in policies.to_dict("records"):
        vehicle_count = random.choices([1, 2, 3], weights=[0.70, 0.25, 0.05], k=1)[0]
        effective_year = pd.to_datetime(policy["EFFECTIVE_DATE"]).year

        for vehicle_sequence in range(1, vehicle_count + 1):
            vehicle_type = random.choices(
                list(VEHICLE_PROFILES),
                weights=[0.40, 0.30, 0.22, 0.08],
                k=1,
            )[0]
            make, model = random.choice(VEHICLE_PROFILES[vehicle_type]["make_models"])
            rows.append(
                {
                    "VEHICLE_ID": f"VEH{vehicle_counter:08d}",
                    "POLICY_ID": policy["POLICY_ID"],
                    "VEHICLE_SEQUENCE": vehicle_sequence,
                    "MODEL_YEAR": random.randint(
                        max(2005, effective_year - 12),
                        effective_year,
                    ),
                    "MAKE": make,
                    "MODEL": model,
                    "VEHICLE_TYPE": vehicle_type,
                    "GARAGING_STATE": policy["PRIMARY_STATE"],
                    "ANNUAL_MILEAGE": random.randint(4_000, 25_000),
                    "USAGE": random.choice(["commute", "pleasure", "business"]),
                    "SAFETY_DEVICE_FLAG": random.choice([0, 1]),
                    "SOURCE_SYSTEM": "vehicle_registry_sim",
                }
            )
            vehicle_counter += 1

    return pd.DataFrame(rows, columns=VEHICLE_COLUMNS)


def generate_raw_driver(policies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    driver_counter = 1

    for policy in policies.to_dict("records"):
        driver_count = random.choices([1, 2, 3], weights=[0.55, 0.35, 0.10], k=1)[0]
        effective_date = pd.to_datetime(policy["EFFECTIVE_DATE"]).to_pydatetime()

        for driver_sequence in range(1, driver_count + 1):
            age_at_effective = random.randint(18, 74)
            licensing_age = random.randint(16, min(21, age_at_effective))
            date_of_birth = effective_date - timedelta(
                days=age_at_effective * 365 + random.randint(0, 364)
            )
            rows.append(
                {
                    "DRIVER_ID": f"DRV{driver_counter:08d}",
                    "POLICY_ID": policy["POLICY_ID"],
                    "DRIVER_SEQUENCE": driver_sequence,
                    "DATE_OF_BIRTH": date_of_birth.date(),
                    "GENDER": random.choices(
                        ["F", "M", "X"],
                        weights=[0.45, 0.45, 0.10],
                        k=1,
                    )[0],
                    "YEARS_LICENSED": max(0, age_at_effective - licensing_age),
                    "PRIOR_ACCIDENTS": int(np.random.poisson(0.18)),
                    "PRIOR_VIOLATIONS": int(np.random.poisson(0.25)),
                    "MARITAL_STATUS": random.choice(["single", "married", "divorced"]),
                    "CREDIT_TIER": random.choice(["A", "B", "C", "D"]),
                    "SOURCE_SYSTEM": "driver_registry_sim",
                }
            )
            driver_counter += 1

    return pd.DataFrame(rows, columns=DRIVER_COLUMNS)


def generate_raw_driver_vehicle_assignment(
    policies: pd.DataFrame,
    vehicles: pd.DataFrame,
    drivers: pd.DataFrame,
) -> pd.DataFrame:
    drivers_by_policy = defaultdict(list)
    for driver in drivers.to_dict("records"):
        drivers_by_policy[driver["POLICY_ID"]].append(driver["DRIVER_ID"])

    vehicles_by_policy = defaultdict(list)
    for vehicle in vehicles.to_dict("records"):
        vehicles_by_policy[vehicle["POLICY_ID"]].append(vehicle["VEHICLE_ID"])

    rows = []
    assignment_counter = 1

    for policy in policies.to_dict("records"):
        policy_drivers = drivers_by_policy[policy["POLICY_ID"]]
        policy_vehicle_ids = vehicles_by_policy[policy["POLICY_ID"]]
        assigned_drivers = set()
        assigned_pairs = set()

        def add_assignment(driver_id: str, vehicle_id: str, assignment_type: str) -> None:
            nonlocal assignment_counter
            pair = (driver_id, vehicle_id)
            if pair in assigned_pairs:
                return
            rows.append(
                {
                    "ASSIGNMENT_ID": f"ASG{assignment_counter:08d}",
                    "POLICY_ID": policy["POLICY_ID"],
                    "DRIVER_ID": driver_id,
                    "VEHICLE_ID": vehicle_id,
                    "ASSIGNMENT_TYPE": assignment_type,
                    "EFFECTIVE_DATE": policy["EFFECTIVE_DATE"],
                    "EXPIRATION_DATE": policy["EXPIRATION_DATE"],
                    "SOURCE_SYSTEM": "policy_admin_auto_sim",
                }
            )
            assigned_pairs.add(pair)
            assigned_drivers.add(driver_id)
            assignment_counter += 1

        for vehicle_index, vehicle_id in enumerate(policy_vehicle_ids):
            primary_driver = policy_drivers[vehicle_index % len(policy_drivers)]
            add_assignment(primary_driver, vehicle_id, "PRIMARY")
            for driver_id in policy_drivers:
                if driver_id != primary_driver and random.random() < 0.50:
                    add_assignment(driver_id, vehicle_id, "OCCASIONAL")

        for driver_id in policy_drivers:
            if driver_id not in assigned_drivers:
                add_assignment(driver_id, random.choice(policy_vehicle_ids), "OCCASIONAL")

    return pd.DataFrame(rows, columns=ASSIGNMENT_COLUMNS)


def generate_raw_property_location(policies: pd.DataFrame) -> pd.DataFrame:
    rows = []
    location_counter = 1

    for policy in policies.to_dict("records"):
        location_count = random.choices(
            [1, 2, 3, 4, 5],
            weights=[0.50, 0.25, 0.12, 0.08, 0.05],
            k=1,
        )[0]
        for location_sequence in range(1, location_count + 1):
            occupancy = weighted_choice(PROPERTY_OCCUPANCIES)
            construction_type = weighted_choice(PROPERTY_CONSTRUCTIONS)
            year_built = random.randint(1950, 2020)
            tiv = round(random.uniform(250_000, 8_000_000), 2)
            rows.append(
                {
                    "LOCATION_ID": f"LOC{location_counter:08d}",
                    "POLICY_ID": policy["POLICY_ID"],
                    "LOCATION_SEQUENCE": location_sequence,
                    "STATE": policy["PRIMARY_STATE"],
                    "ZIP_CODE": f"{random.randint(10000, 99999):05d}",
                    "OCCUPANCY": occupancy,
                    "CONSTRUCTION_TYPE": construction_type,
                    "YEAR_BUILT": year_built,
                    "PROTECTION_CLASS": random.randint(1, 10),
                    "TOTAL_INSURED_VALUE": tiv,
                    "SOURCE_SYSTEM": "property_registry_sim",
                }
            )
            location_counter += 1

    return pd.DataFrame(rows, columns=PROPERTY_LOCATION_COLUMNS)


def _generate_risk_units(
    policies: pd.DataFrame,
    source_entities: pd.DataFrame,
    risk_unit_type: str,
    exposure_unit: str,
    source_id_column: str,
    source_system: str,
    risk_namespace: str,
) -> pd.DataFrame:
    policy_lookup = {row["POLICY_ID"]: row for row in policies.to_dict("records")}
    rows = []

    for risk_counter, entity in enumerate(source_entities.to_dict("records"), start=1):
        policy = policy_lookup[entity["POLICY_ID"]]
        rows.append(
            {
                "RISK_UNIT_ID": f"RISK_{risk_namespace}_{risk_counter:08d}",
                "POLICY_ID": policy["POLICY_ID"],
                "RISK_UNIT_TYPE": risk_unit_type,
                "SOURCE_RISK_UNIT_ID": entity[source_id_column],
                "EFFECTIVE_DATE": policy["EFFECTIVE_DATE"],
                "EXPIRATION_DATE": policy["EXPIRATION_DATE"],
                "STATUS": policy["STATUS"],
                "EXPOSURE_UNIT": exposure_unit,
                "SOURCE_SYSTEM": source_system,
            }
        )

    return pd.DataFrame(rows, columns=RISK_UNIT_COLUMNS)


def generate_auto_risk_units(
    policies: pd.DataFrame,
    vehicles: pd.DataFrame,
    risk_namespace: str = "PA",
) -> pd.DataFrame:
    return _generate_risk_units(
        policies,
        vehicles,
        risk_unit_type="vehicle",
        exposure_unit="car_year",
        source_id_column="VEHICLE_ID",
        source_system="policy_admin_auto_sim",
        risk_namespace=risk_namespace,
    )


def generate_property_risk_units(
    policies: pd.DataFrame,
    locations: pd.DataFrame,
    risk_namespace: str = "CP",
) -> pd.DataFrame:
    return _generate_risk_units(
        policies,
        locations,
        risk_unit_type="property_location",
        exposure_unit="location_year",
        source_id_column="LOCATION_ID",
        source_system="policy_admin_property_sim",
        risk_namespace=risk_namespace,
    )


def _driver_age_at_effective(
    driver: dict,
    effective_date: object,
) -> int:
    birth_date = pd.to_datetime(driver["DATE_OF_BIRTH"])
    effective = pd.to_datetime(effective_date)
    return max(16, effective.year - birth_date.year)


def _select_auto_coverages(vehicle: dict, effective_date: object) -> list[str]:
    vehicle_age = max(
        0,
        pd.to_datetime(effective_date).year - int(vehicle["MODEL_YEAR"]),
    )
    selected = ["AUTO_BI", "AUTO_PD"]

    collision_probability = (
        0.80 if vehicle_age <= 5 else 0.60 if vehicle_age <= 10 else 0.35
    )
    if random.random() < collision_probability:
        selected.append("AUTO_COLL")
    if random.random() < AUTO_COVERAGES["AUTO_COMP"]["selection_probability"]:
        selected.append("AUTO_COMP")

    return selected


def _auto_pricing_factors(
    policy: dict,
    vehicle: dict,
    driver: dict,
    effective_date: object,
    coverage: dict,
) -> tuple[float, float]:
    state_factors = {
        "CA": 1.10, "TX": 1.00, "FL": 1.20, "NY": 1.25, "IL": 1.05,
        "PA": 0.95, "OH": 0.90, "GA": 1.00, "NC": 0.90, "MI": 1.30,
    }
    state_factor = state_factors.get(policy["PRIMARY_STATE"], 1.00)
    driver_age = _driver_age_at_effective(driver, effective_date)
    driver_factor = (
        1.25 if driver_age < 25 else 0.90 if driver_age >= 50 else 1.00
    )
    driver_factor *= 1 + 0.08 * min(driver["PRIOR_ACCIDENTS"], 5)
    usage_factor = {
        "commute": 1.05,
        "pleasure": 0.90,
        "business": 1.15,
    }[vehicle["USAGE"]]
    deductible_factor = AUTO_DEDUCTIBLE_TABLE.get(coverage["deductible"], 0.90)
    limit_factor = AUTO_LIMIT_TABLE.get(coverage["limit"], 1.00)
    pricing_factor = (
        state_factor
        * driver_factor
        * VEHICLE_PROFILES[vehicle["VEHICLE_TYPE"]]["pricing_factor"]
        * usage_factor
        * deductible_factor
        * limit_factor
        * UNDERWRITING_TIERS[policy["UNDERWRITING_TIER"]]["premium_multiplier"]
        * severity_trend_factor(
            pd.to_datetime(effective_date).to_pydatetime(),
            AUTO_PREMIUM_TREND,
        )
    )
    true_risk_factor = (
        (1.40 if driver_age < 25 else 0.95 if driver_age >= 50 else 1.00)
        * (1 + 0.10 * min(driver["PRIOR_ACCIDENTS"], 5))
        * VEHICLE_PROFILES[vehicle["VEHICLE_TYPE"]]["true_risk_factor"]
    )
    return pricing_factor, true_risk_factor


def generate_auto_coverages(
    policies: pd.DataFrame,
    risk_units: pd.DataFrame,
    vehicles: pd.DataFrame,
    drivers: pd.DataFrame,
    assignments: pd.DataFrame,
    coverage_namespace: str = "PA",
) -> pd.DataFrame:
    policy_lookup = {row["POLICY_ID"]: row for row in policies.to_dict("records")}
    vehicle_lookup = {row["VEHICLE_ID"]: row for row in vehicles.to_dict("records")}
    driver_lookup = {row["DRIVER_ID"]: row for row in drivers.to_dict("records")}
    primary_driver_by_vehicle = {}
    for assignment in assignments.to_dict("records"):
        if (
            assignment["ASSIGNMENT_TYPE"] == "PRIMARY"
            or assignment["VEHICLE_ID"] not in primary_driver_by_vehicle
        ):
            primary_driver_by_vehicle[assignment["VEHICLE_ID"]] = assignment["DRIVER_ID"]

    rows = []
    coverage_counter = 1
    for risk_unit in risk_units.to_dict("records"):
        policy = policy_lookup[risk_unit["POLICY_ID"]]
        vehicle = vehicle_lookup[risk_unit["SOURCE_RISK_UNIT_ID"]]
        driver = driver_lookup[primary_driver_by_vehicle[vehicle["VEHICLE_ID"]]]
        coverage_effective_date = policy["EFFECTIVE_DATE"]
        coverage_expiration_date = policy["EXPIRATION_DATE"]
        term_factor = coverage_term_factor(
            coverage_effective_date,
            coverage_expiration_date,
        )
        for coverage_code in _select_auto_coverages(
            vehicle,
            policy["EFFECTIVE_DATE"],
        ):
            coverage = AUTO_COVERAGES[coverage_code]
            pricing_factor, _ = _auto_pricing_factors(
                policy,
                vehicle,
                driver,
                policy["EFFECTIVE_DATE"],
                coverage,
            )
            rows.append(
                {
                    "COVERAGE_ID": f"COV_{coverage_namespace}_{coverage_counter:08d}",
                    "POLICY_ID": policy["POLICY_ID"],
                    "RISK_UNIT_ID": risk_unit["RISK_UNIT_ID"],
                    "COVERAGE_CODE": coverage_code,
                    "COVERAGE_FAMILY": coverage["coverage_family"],
                    "EFFECTIVE_DATE": coverage_effective_date,
                    "EXPIRATION_DATE": coverage_expiration_date,
                    "LIMIT_AMOUNT": coverage["limit"],
                    "DEDUCTIBLE_AMOUNT": coverage["deductible"],
                    "WRITTEN_PREMIUM": round(
                        coverage["base_rate"] * pricing_factor * term_factor,
                        2,
                    ),
                    "SOURCE_SYSTEM": "policy_admin_auto_sim",
                }
            )
            coverage_counter += 1

    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)


def generate_property_coverages(
    policies: pd.DataFrame,
    risk_units: pd.DataFrame,
    locations: pd.DataFrame,
    coverage_namespace: str = "CP",
) -> pd.DataFrame:
    policy_lookup = {row["POLICY_ID"]: row for row in policies.to_dict("records")}
    location_lookup = {row["LOCATION_ID"]: row for row in locations.to_dict("records")}
    rows = []
    coverage_counter = 1

    for risk_unit in risk_units.to_dict("records"):
        policy = policy_lookup[risk_unit["POLICY_ID"]]
        location = location_lookup[risk_unit["SOURCE_RISK_UNIT_ID"]]
        coverage_effective_date = policy["EFFECTIVE_DATE"]
        coverage_expiration_date = policy["EXPIRATION_DATE"]
        term_factor = coverage_term_factor(
            coverage_effective_date,
            coverage_expiration_date,
        )
        occupancy = PROPERTY_OCCUPANCIES[location["OCCUPANCY"]]
        construction = PROPERTY_CONSTRUCTIONS[location["CONSTRUCTION_TYPE"]]
        state_factor = PROPERTY_PRICING_FACTORS["state"].get(
            location["STATE"],
            1.00,
        )

        for coverage_code, coverage in PROPERTY_COVERAGES.items():
            if random.random() > coverage["selection_probability"]:
                continue
            limit_amount = round(
                location["TOTAL_INSURED_VALUE"] * coverage["limit_factor"],
                2,
            )
            pricing_factor = (
                occupancy["premium_factor"]
                * construction["premium_factor"]
                * state_factor
                * UNDERWRITING_TIERS[policy["UNDERWRITING_TIER"]]["premium_multiplier"]
                * severity_trend_factor(
                    pd.to_datetime(policy["EFFECTIVE_DATE"]).to_pydatetime(),
                    PROPERTY_PREMIUM_TREND,
                )
            )
            rows.append(
                {
                    "COVERAGE_ID": f"COV_{coverage_namespace}_{coverage_counter:08d}",
                    "POLICY_ID": policy["POLICY_ID"],
                    "RISK_UNIT_ID": risk_unit["RISK_UNIT_ID"],
                    "COVERAGE_CODE": coverage_code,
                    "COVERAGE_FAMILY": coverage["coverage_family"],
                    "EFFECTIVE_DATE": coverage_effective_date,
                    "EXPIRATION_DATE": coverage_expiration_date,
                    "LIMIT_AMOUNT": limit_amount,
                    "DEDUCTIBLE_AMOUNT": coverage["deductible"],
                    "WRITTEN_PREMIUM": round(
                        limit_amount
                        * coverage["base_rate"]
                        * pricing_factor
                        * term_factor,
                        2,
                    ),
                    "SOURCE_SYSTEM": "policy_admin_property_sim",
                }
            )
            coverage_counter += 1

    return pd.DataFrame(rows, columns=COVERAGE_COLUMNS)


def _coverage_lookup(coverages: pd.DataFrame) -> dict[tuple[str, str], dict]:
    return {
        (row["RISK_UNIT_ID"], row["COVERAGE_CODE"]): row
        for row in coverages.to_dict("records")
    }


def _coverage_codes_by_risk_unit(coverages: pd.DataFrame) -> dict[str, set[str]]:
    result = defaultdict(set)
    for row in coverages.to_dict("records"):
        result[row["RISK_UNIT_ID"]].add(row["COVERAGE_CODE"])
    return result


def _claim_status(reported_date: datetime, closure_months: int) -> str:
    closed_date = (
        pd.Timestamp(reported_date)
        + pd.DateOffset(months=closure_months)
    ).to_pydatetime()
    return "closed" if closed_date <= END_DATE else "open"


def _coverage_terms(ground_up_loss: float, coverage: dict) -> float:
    after_deductible = max(
        ground_up_loss - float(coverage["DEDUCTIBLE_AMOUNT"]),
        0.0,
    )
    return round(min(after_deductible, float(coverage["LIMIT_AMOUNT"])), 2)


def _append_claim(
    rows: list[dict],
    claim_id: str,
    policy: dict,
    risk_unit: dict,
    coverage: dict,
    loss_date: datetime,
    reported_date: datetime,
    claim_type: str,
    cause_code: str,
    closure_months: int,
) -> None:
    rows.append(
        {
            "CLAIM_ID": claim_id,
            "POLICY_ID": policy["POLICY_ID"],
            "RISK_UNIT_ID": risk_unit["RISK_UNIT_ID"],
            "COVERAGE_ID": coverage["COVERAGE_ID"],
            "COVERAGE_CODE": coverage["COVERAGE_CODE"],
            "LOSS_DATE": loss_date.date(),
            "REPORTED_DATE": reported_date.date(),
            "CLAIM_TYPE": claim_type,
            "CAUSE_CODE": cause_code,
            "CLAIM_STATUS": _claim_status(reported_date, closure_months),
            "SOURCE_SYSTEM": PRODUCT_CONFIG[
                policy["LINE_OF_BUSINESS"]
            ]["claim_source_system"],
        }
    )


def generate_auto_claims(
    policies: pd.DataFrame,
    risk_units: pd.DataFrame,
    coverages: pd.DataFrame,
    vehicles: pd.DataFrame,
    drivers: pd.DataFrame,
    assignments: pd.DataFrame,
    claim_namespace: str = "PA",
) -> tuple[pd.DataFrame, dict[str, dict]]:
    policy_lookup = {row["POLICY_ID"]: row for row in policies.to_dict("records")}
    vehicle_lookup = {row["VEHICLE_ID"]: row for row in vehicles.to_dict("records")}
    driver_lookup = {row["DRIVER_ID"]: row for row in drivers.to_dict("records")}
    drivers_by_vehicle = defaultdict(list)
    primary_driver_by_vehicle = {}
    for assignment in assignments.to_dict("records"):
        vehicle_id = assignment["VEHICLE_ID"]
        drivers_by_vehicle[vehicle_id].append(assignment["DRIVER_ID"])
        if (
            assignment["ASSIGNMENT_TYPE"] == "PRIMARY"
            or vehicle_id not in primary_driver_by_vehicle
        ):
            primary_driver_by_vehicle[vehicle_id] = assignment["DRIVER_ID"]
    coverage_lookup = _coverage_lookup(coverages)
    coverage_codes_by_risk_unit = _coverage_codes_by_risk_unit(coverages)
    rows = []
    claim_meta = {}
    claim_counter = 1

    for risk_unit in risk_units.to_dict("records"):
        policy = policy_lookup[risk_unit["POLICY_ID"]]
        vehicle = vehicle_lookup[risk_unit["SOURCE_RISK_UNIT_ID"]]
        assigned_driver_ids = drivers_by_vehicle[vehicle["VEHICLE_ID"]]
        frequency_driver = driver_lookup[
            primary_driver_by_vehicle[vehicle["VEHICLE_ID"]]
        ]
        driver_age = _driver_age_at_effective(
            frequency_driver,
            policy["EFFECTIVE_DATE"],
        )
        _, risk_end, exposure_years = risk_exposure_window(policy, risk_unit)
        if exposure_years <= 0:
            continue
        true_risk_factor = (
            1.40 if driver_age < 25 else 0.95 if driver_age >= 50 else 1.00
        )
        true_risk_factor *= 1 + 0.10 * min(
            frequency_driver["PRIOR_ACCIDENTS"],
            5,
        )
        true_risk_factor *= VEHICLE_PROFILES[
            vehicle["VEHICLE_TYPE"]
        ]["true_risk_factor"]
        annual_probability = 0.12 * true_risk_factor
        available = coverage_codes_by_risk_unit[risk_unit["RISK_UNIT_ID"]]
        effective_date = pd.to_datetime(
            risk_unit["EFFECTIVE_DATE"]
        ).to_pydatetime()

        for scenario in AUTO_CLAIM_SCENARIOS:
            if scenario["coverage_code"] not in available:
                continue
            scenario_count = np.random.poisson(
                annual_probability
                * scenario["weight"]
                * exposure_years
            )
            coverage = coverage_lookup[
                (risk_unit["RISK_UNIT_ID"], scenario["coverage_code"])
            ]
            for _ in range(scenario_count):
                claim_driver_id = random.choice(assigned_driver_ids)
                claim_id = f"CLM_{claim_namespace}_{claim_counter:08d}"
                claim_counter += 1
                loss_date = rand_date(effective_date, risk_end)
                reported_date = min(
                    loss_date + timedelta(days=random.randint(1, 10)),
                    END_DATE,
                )
                ground_up_loss = float(
                    np.random.lognormal(
                        mean=np.log(scenario["severity"]),
                        sigma=0.60,
                    )
                    * severity_trend_factor(loss_date, AUTO_SEVERITY_TREND)
                )
                covered_ultimate = _coverage_terms(ground_up_loss, coverage)
                claim_meta[claim_id] = {
                    "ultimate": covered_ultimate,
                    "ground_up_loss": round(ground_up_loss, 2),
                    "driver_id": claim_driver_id,
                    "payment_pattern": AUTO_PAYMENT_PATTERN,
                    "reserve_pattern": AUTO_RESERVE_PATTERN,
                    "development_months": AUTO_DEVELOPMENT_MONTHS,
                    "closure_months": max(AUTO_DEVELOPMENT_MONTHS),
                    "recovery_ratio": scenario["recovery_ratio"],
                    "paid_expense_ratio": 0.10,
                    "case_expense_ratio": 0.08,
                }
                _append_claim(
                    rows,
                    claim_id,
                    policy,
                    risk_unit,
                    coverage,
                    loss_date,
                    reported_date,
                    scenario["claim_type"],
                    scenario["cause_code"],
                    max(AUTO_DEVELOPMENT_MONTHS),
                )

    return pd.DataFrame(rows, columns=CLAIM_COLUMNS), claim_meta


def generate_property_claims(
    policies: pd.DataFrame,
    risk_units: pd.DataFrame,
    coverages: pd.DataFrame,
    locations: pd.DataFrame,
    claim_namespace: str = "CP",
) -> tuple[pd.DataFrame, dict[str, dict]]:
    policy_lookup = {row["POLICY_ID"]: row for row in policies.to_dict("records")}
    location_lookup = {row["LOCATION_ID"]: row for row in locations.to_dict("records")}
    coverage_lookup = _coverage_lookup(coverages)
    coverage_codes_by_risk_unit = _coverage_codes_by_risk_unit(coverages)
    rows = []
    claim_meta = {}
    claim_counter = 1

    for risk_unit in risk_units.to_dict("records"):
        policy = policy_lookup[risk_unit["POLICY_ID"]]
        location = location_lookup[risk_unit["SOURCE_RISK_UNIT_ID"]]
        occupancy = PROPERTY_OCCUPANCIES[location["OCCUPANCY"]]
        construction = PROPERTY_CONSTRUCTIONS[location["CONSTRUCTION_TYPE"]]
        _, risk_end, exposure_years = risk_exposure_window(policy, risk_unit)
        if exposure_years <= 0:
            continue
        state_true_factor = PROPERTY_TRUE_RISK_FACTORS["state"].get(
            location["STATE"],
            1.00,
        )
        protection_true_factor = PROPERTY_TRUE_RISK_FACTORS[
            "protection_class"
        ][int(location["PROTECTION_CLASS"])]
        annual_probability = (
            0.08
            * occupancy["frequency_factor"]
            * construction["frequency_factor"]
            * state_true_factor
            * protection_true_factor
        )
        available = coverage_codes_by_risk_unit[risk_unit["RISK_UNIT_ID"]]
        effective_date = pd.to_datetime(
            risk_unit["EFFECTIVE_DATE"]
        ).to_pydatetime()

        for scenario in PROPERTY_CLAIM_SCENARIOS:
            if scenario["coverage_code"] not in available:
                continue
            scenario_count = np.random.poisson(
                annual_probability
                * scenario["weight"]
                * exposure_years
            )
            coverage = coverage_lookup[
                (risk_unit["RISK_UNIT_ID"], scenario["coverage_code"])
            ]
            for _ in range(scenario_count):
                claim_id = f"CLM_{claim_namespace}_{claim_counter:08d}"
                claim_counter += 1
                loss_date = rand_date(effective_date, risk_end)
                reported_date = min(
                    loss_date + timedelta(days=random.randint(1, 15)),
                    END_DATE,
                )
                damage_ratio = np.random.beta(
                    scenario["damage_alpha"],
                    scenario["damage_beta"],
                )
                ground_up_loss = (
                    location["TOTAL_INSURED_VALUE"]
                    * damage_ratio
                    * occupancy["severity_factor"]
                    * severity_trend_factor(loss_date, PROPERTY_SEVERITY_TREND)
                )
                covered_ultimate = _coverage_terms(ground_up_loss, coverage)
                claim_meta[claim_id] = {
                    "ultimate": covered_ultimate,
                    "ground_up_loss": round(ground_up_loss, 2),
                    "payment_pattern": PROPERTY_PAYMENT_PATTERN,
                    "reserve_pattern": PROPERTY_RESERVE_PATTERN,
                    "development_months": PROPERTY_DEVELOPMENT_MONTHS,
                    "closure_months": max(PROPERTY_DEVELOPMENT_MONTHS),
                    "recovery_ratio": scenario["recovery_ratio"],
                    "paid_expense_ratio": 0.12,
                    "case_expense_ratio": 0.10,
                }
                _append_claim(
                    rows,
                    claim_id,
                    policy,
                    risk_unit,
                    coverage,
                    loss_date,
                    reported_date,
                    scenario["claim_type"],
                    scenario["cause_code"],
                    max(PROPERTY_DEVELOPMENT_MONTHS),
                )

    return pd.DataFrame(rows, columns=CLAIM_COLUMNS), claim_meta


def _id_namespace(identifier: str) -> str:
    parts = identifier.split("_")
    return parts[1] if len(parts) > 1 else "GEN"


def generate_raw_premium_transaction(
    policies: pd.DataFrame,
    coverages: pd.DataFrame,
) -> pd.DataFrame:
    policy_lookup = {row["POLICY_ID"]: row for row in policies.to_dict("records")}
    rows = []
    transaction_counter_by_namespace = defaultdict(int)

    for coverage in coverages.to_dict("records"):
        policy = policy_lookup[coverage["POLICY_ID"]]
        policy_end = actual_end_date(policy)
        effective_date = pd.to_datetime(coverage["EFFECTIVE_DATE"]).to_pydatetime()
        expiration_date = pd.to_datetime(coverage["EXPIRATION_DATE"]).to_pydatetime()
        cancellation_date = (
            pd.to_datetime(policy["CANCELLATION_DATE"]).to_pydatetime()
            if pd.notna(policy["CANCELLATION_DATE"])
            else None
        )
        transactions = [
            {
                "TRANSACTION_TYPE": "NEW_BUSINESS",
                "TRANSACTION_DATE": effective_date,
                "PREMIUM_CHANGE": float(coverage["WRITTEN_PREMIUM"]),
                "TRANSACTION_REASON": "new_policy",
            }
        ]

        if policy_end > effective_date + timedelta(days=120) and random.random() < 0.25:
            endorsement_date = effective_date + timedelta(days=random.randint(90, 180))
            if endorsement_date < policy_end and (
                cancellation_date is None or endorsement_date < cancellation_date
            ):
                transactions.append(
                    {
                        "TRANSACTION_TYPE": "ENDORSEMENT",
                        "TRANSACTION_DATE": endorsement_date,
                        "PREMIUM_CHANGE": round(
                            float(coverage["WRITTEN_PREMIUM"])
                            * random.uniform(0.05, 0.20),
                            2,
                        ),
                        "TRANSACTION_REASON": "coverage_change",
                    }
                )

        if cancellation_date is not None:
            remaining_days = max((expiration_date - cancellation_date).days, 0)
            refund_amount = 0.0
            for transaction in transactions:
                premium_change = float(transaction["PREMIUM_CHANGE"])
                if premium_change <= 0:
                    continue
                premium_start = pd.to_datetime(
                    transaction["TRANSACTION_DATE"]
                ).to_pydatetime()
                term_days = max((expiration_date - premium_start).days, 1)
                refund_amount += premium_change * remaining_days / term_days

            transactions.append(
                {
                    "TRANSACTION_TYPE": "CANCELLATION",
                    "TRANSACTION_DATE": cancellation_date,
                    "PREMIUM_CHANGE": round(-refund_amount, 2),
                    "TRANSACTION_REASON": "pro_rata_cancellation_refund",
                }
            )

        cumulative_premium = 0.0
        namespace = _id_namespace(coverage["COVERAGE_ID"])
        for transaction in sorted(transactions, key=lambda item: item["TRANSACTION_DATE"]):
            cumulative_premium += transaction["PREMIUM_CHANGE"]
            transaction_counter_by_namespace[namespace] += 1
            rows.append(
                {
                    "TRANSACTION_ID": (
                        f"PREM_{namespace}_"
                        f"{transaction_counter_by_namespace[namespace]:08d}"
                    ),
                    "POLICY_ID": coverage["POLICY_ID"],
                    "COVERAGE_ID": coverage["COVERAGE_ID"],
                    "TRANSACTION_TYPE": transaction["TRANSACTION_TYPE"],
                    "TRANSACTION_DATE": transaction["TRANSACTION_DATE"].date(),
                    "TRANSACTION_REASON": transaction["TRANSACTION_REASON"],
                    "PREMIUM_CHANGE": round(transaction["PREMIUM_CHANGE"], 2),
                    "CUMULATIVE_PREMIUM": round(max(cumulative_premium, 0), 2),
                    "SOURCE_SYSTEM": "billing_sim",
                }
            )

    return pd.DataFrame(rows, columns=PREMIUM_TRANSACTION_COLUMNS)


def generate_raw_claim_transaction(
    claims: pd.DataFrame,
    simulated_claim_meta: dict[str, dict],
) -> pd.DataFrame:
    if claims.empty:
        return pd.DataFrame(columns=CLAIM_TRANSACTION_COLUMNS)

    rows = []
    transaction_counter_by_namespace = defaultdict(int)
    for claim in claims.to_dict("records"):
        meta = simulated_claim_meta[claim["CLAIM_ID"]]
        ultimate = meta["ultimate"]
        paid_expense_ratio = meta.get("paid_expense_ratio", 0.10)
        case_expense_ratio = meta.get("case_expense_ratio", 0.08)
        recovery_ratio = meta.get("recovery_ratio", 0.0)
        reported_date = pd.to_datetime(claim["REPORTED_DATE"]).to_pydatetime()
        previous_paid_loss = 0.0
        previous_case_reserve = 0.0
        previous_case_expense = 0.0

        for index, (paid_pct, reserve_pct, development_month) in enumerate(
            zip(
                meta["payment_pattern"],
                meta["reserve_pattern"],
                meta["development_months"],
            )
        ):
            transaction_date = reported_date + timedelta(days=30 * development_month)
            if transaction_date > END_DATE:
                continue

            cumulative_paid_loss = round(ultimate * paid_pct, 2)
            current_case_reserve = round(ultimate * reserve_pct, 2)
            paid_loss_change = round(cumulative_paid_loss - previous_paid_loss, 2)
            case_reserve_change = round(current_case_reserve - previous_case_reserve, 2)
            paid_expense_change = round(
                paid_loss_change * paid_expense_ratio,
                2,
            )
            current_case_expense = round(
                current_case_reserve * case_expense_ratio,
                2,
            )
            case_expense_change = round(
                current_case_expense - previous_case_expense,
                2,
            )
            recovery_change = round(
                paid_loss_change * recovery_ratio,
                2,
            )
            incurred_loss_change = round(
                paid_loss_change
                + case_reserve_change
                + paid_expense_change
                + case_expense_change
                - recovery_change,
                2,
            )
            transaction_type = "RESERVE_SET" if index == 0 else "PAYMENT"
            namespace = _id_namespace(claim["CLAIM_ID"])
            transaction_counter_by_namespace[namespace] += 1
            rows.append(
                {
                    "TRANSACTION_ID": (
                        f"CLMT_{namespace}_"
                        f"{transaction_counter_by_namespace[namespace]:08d}"
                    ),
                    "CLAIM_ID": claim["CLAIM_ID"],
                    "TRANSACTION_TYPE": transaction_type,
                    "TRANSACTION_DATE": transaction_date.date(),
                    "PAID_LOSS_CHANGE": paid_loss_change,
                    "CASE_RESERVE_CHANGE": case_reserve_change,
                    "PAID_EXPENSE_CHANGE": paid_expense_change,
                    "CASE_EXPENSE_CHANGE": case_expense_change,
                    "RECOVERY_CHANGE": recovery_change,
                    "INCURRED_LOSS_CHANGE": incurred_loss_change,
                    "SOURCE_SYSTEM": "claims_admin_transaction_sim",
                }
            )
            previous_paid_loss = cumulative_paid_loss
            previous_case_reserve = current_case_reserve
            previous_case_expense = current_case_expense

    return pd.DataFrame(rows, columns=CLAIM_TRANSACTION_COLUMNS)


def generate_raw_data(
    n_auto: int = N_AUTO_POLICIES,
    n_property: int = N_PROPERTY_POLICIES,
) -> dict[str, pd.DataFrame]:
    policies = generate_raw_policy(n_auto, n_property)
    auto_policies = policies[policies["LINE_OF_BUSINESS"] == "personal_auto"].copy()
    property_policies = policies[
        policies["LINE_OF_BUSINESS"] == "commercial_property"
    ].copy()

    vehicles = generate_raw_vehicle(auto_policies)
    drivers = generate_raw_driver(auto_policies)
    assignments = generate_raw_driver_vehicle_assignment(
        auto_policies,
        vehicles,
        drivers,
    )

    locations = generate_raw_property_location(property_policies)

    auto_risk_units = generate_auto_risk_units(
        auto_policies,
        vehicles,
        risk_namespace="PA",
    )
    property_risk_units = generate_property_risk_units(
        property_policies,
        locations,
        risk_namespace="CP",
    )
    risk_units = concat_with_schema(
        [auto_risk_units, property_risk_units],
        RISK_UNIT_COLUMNS,
    )

    auto_coverages = generate_auto_coverages(
        auto_policies,
        auto_risk_units,
        vehicles,
        drivers,
        assignments,
        coverage_namespace="PA",
    )
    property_coverages = generate_property_coverages(
        property_policies,
        property_risk_units,
        locations,
        coverage_namespace="CP",
    )
    coverages = concat_with_schema(
        [auto_coverages, property_coverages],
        COVERAGE_COLUMNS,
    )

    auto_claims, auto_claim_meta = generate_auto_claims(
        auto_policies,
        auto_risk_units,
        auto_coverages,
        vehicles,
        drivers,
        assignments,
        claim_namespace="PA",
    )
    property_claims, property_claim_meta = generate_property_claims(
        property_policies,
        property_risk_units,
        property_coverages,
        locations,
        claim_namespace="CP",
    )
    claims = concat_with_schema(
        [auto_claims, property_claims],
        CLAIM_COLUMNS,
    )

    simulated_claim_meta = {
        **auto_claim_meta,
        **property_claim_meta,
    }
    premium_transactions = generate_raw_premium_transaction(policies, coverages)
    claim_transactions = generate_raw_claim_transaction(
        claims,
        simulated_claim_meta,
    )

    return {
        "raw_policy": policies,
        "raw_policy_risk_unit": risk_units,
        "raw_policy_coverage": coverages,
        "raw_premium_transaction": premium_transactions,
        "raw_claim": claims,
        "raw_claim_transaction": claim_transactions,
        "raw_vehicle": vehicles,
        "raw_driver": drivers,
        "raw_driver_vehicle_assignment": assignments,
        "raw_property_location": locations,
    }


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_connection():
    private_key_path = Path(get_env("SNOWFLAKE_PRIVATE_KEY_PATH"))
    if not private_key_path.is_absolute():
        private_key_path = Path(__file__).resolve().parent / private_key_path
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend(),
        ).private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    return snowflake.connector.connect(
        user=get_env("SNOWFLAKE_USER"),
        account=get_env("SNOWFLAKE_ACCOUNT"),
        role=get_env("SNOWFLAKE_ROLE"),
        warehouse=get_env("SNOWFLAKE_WAREHOUSE"),
        database=get_env("SNOWFLAKE_DATABASE"),
        schema=get_env("SNOWFLAKE_SCHEMA"),
        private_key=private_key,
    )


def load_dataframe_to_snowflake(conn, df: pd.DataFrame, table_name: str) -> None:
    success, _, row_count, _ = write_pandas(
        conn,
        df,
        table_name.upper(),
        auto_create_table=True,
        overwrite=True,
        use_logical_type=True,
        # quote_identifiers=False,
    )
    if not success:
        raise RuntimeError(f"Failed to load data into {table_name}")
    print(f"{table_name}: {row_count:,} rows loaded")


def print_snowflake_context(conn) -> None:
    """Print the exact Snowflake target so the UI lookup uses the same context."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "select current_database(), current_schema(), current_role(), "
            "current_warehouse()"
        )
        database, schema, role, warehouse = cursor.fetchone()
        print(
            "Snowflake target: "
            f"{database}.{schema} (role={role}, warehouse={warehouse})"
        )
    finally:
        cursor.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate multi-line insurance raw operational data"
    )
    parser.add_argument(
        "--n-auto",
        "--n",
        dest="n_auto",
        type=int,
        default=N_AUTO_POLICIES,
        help="Number of Personal Auto policies to generate (default: 50000)",
    )
    parser.add_argument(
        "--n-property",
        dest="n_property",
        type=int,
        default=N_PROPERTY_POLICIES,
        help="Number of Commercial Property policies to generate (default: 20000)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("RAW_OUTPUT_DIR", "./output"),
        help="Directory for generated CSV files",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Generate CSV files without connecting to Snowflake",
    )
    parser.add_argument(
        "--batch-id",
        default=os.getenv("LOAD_BATCH_ID"),
        help="Audit batch ID (defaults to a UTC timestamp-based ID)",
    )
    args = parser.parse_args()
    if args.n_auto < 0 or args.n_property < 0:
        parser.error("--n-auto and --n-property cannot be negative")
    if args.n_auto == 0 and args.n_property == 0:
        parser.error("At least one policy count must be greater than zero")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_tables = generate_raw_data(args.n_auto, args.n_property)
    ingested_at = datetime.now(timezone.utc)
    load_batch_id = args.batch_id or f"REBUILD_{ingested_at:%Y%m%dT%H%M%SZ}"
    add_load_metadata(raw_tables, load_batch_id, ingested_at)

    for table_name, df in raw_tables.items():
        df.to_csv(output_dir / f"{table_name}.csv", index=False)
        print(f"{table_name}: {len(df):,} rows generated")

    if args.no_upload:
        return

    conn = build_connection()
    try:
        print_snowflake_context(conn)
        for table_name, df in raw_tables.items():
            load_dataframe_to_snowflake(conn, df, table_name.upper())
    finally:
        conn.close()


if __name__ == "__main__":
    main()
