"""
Insurance Analytics Platform - Production Style Simulated Data Generator
Actuarial-ready structure:
- Policy dimension
- Claim transaction fact (development simulation)
- Rate level history
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
import os
import csv
from snowflake.connector.pandas_tools import write_pandas
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

random.seed(42)
np.random.seed(42)
load_dotenv()

# ─────────────────────────────────────────
# Read environment variables
# ─────────────────────────────────────────

SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
PRIVATE_KEY_PATH = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

if not all([
    SNOWFLAKE_USER,
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_WAREHOUSE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    PRIVATE_KEY_PATH
]):
    raise ValueError("Missing one or more required Snowflake environment variables.")

# ─────────────────────────────────────────
# Load private key
# ─────────────────────────────────────────

with open(PRIVATE_KEY_PATH, "rb") as key:
    p_key = serialization.load_pem_private_key(
        key.read(),
        password=None,
        backend=default_backend()
    )

private_key = p_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# ─────────────────────────────────────────
# Connect
# ─────────────────────────────────────────

conn = snowflake.connector.connect(
    user=SNOWFLAKE_USER,
    account=SNOWFLAKE_ACCOUNT,
    warehouse=SNOWFLAKE_WAREHOUSE,
    database=SNOWFLAKE_DATABASE,
    schema=SNOWFLAKE_SCHEMA,
    private_key=private_key
)

print("Connected to Snowflake securely using environment variables.")

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────

N_POLICIES = 50_000
CLAIM_FREQUENCY = 0.12   # 12% annual freq approx
START_DATE = datetime(2019, 1, 1)
END_DATE = datetime(2023, 12, 31)

# ─────────────────────────────────────────────────────────
# REFERENCE TABLES
# ─────────────────────────────────────────────────────────

STATES = ["CA","TX","FL","NY","IL","PA","OH","GA","NC","MI"]

RISK_CLASSES = {
    "preferred":  {"weight": 0.30, "freq_mult": 0.7,  "prem_mult": 0.8},
    "standard":   {"weight": 0.45, "freq_mult": 1.0,  "prem_mult": 1.0},
    "nonstandard":{"weight": 0.20, "freq_mult": 1.5,  "prem_mult": 1.3},
    "commercial": {"weight": 0.05, "freq_mult": 1.8,  "prem_mult": 2.5},
}

VEHICLE_SEGMENTS = {
    "sedan": 1100,
    "suv": 1300,
    "truck": 1200,
    "sports": 1600,
}

# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def rand_date(start, end):
    return start + timedelta(days=random.randint(0, (end-start).days))

def weighted_choice(d, weight_key="weight"):
    keys = list(d.keys())
    weights = [d[k][weight_key] for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]

# ─────────────────────────────────────────────────────────
# POLICY GENERATION
# ─────────────────────────────────────────────────────────

def generate_policies(n):
    rows = []

    for i in range(n):
        pid = f"POL{i+1:08d}"

        risk = weighted_choice(RISK_CLASSES)
        vehicle = random.choice(list(VEHICLE_SEGMENTS.keys()))
        state = random.choice(STATES)

        eff = rand_date(START_DATE, datetime(2023,6,30))
        term = random.choice([6,12])
        exp = eff + timedelta(days=term*30)

        cancel = None
        status = "active"

        if random.random() < 0.08:
            cancel = rand_date(eff, exp)
            status = "cancelled"
        elif exp <= END_DATE:
            status = "expired"

        # pricing trend 3% per year
        years = (eff - START_DATE).days / 365
        trend = 1.03 ** years

        base = VEHICLE_SEGMENTS[vehicle]
        prem = base * RISK_CLASSES[risk]["prem_mult"] * trend
        prem *= random.uniform(0.9, 1.1)

        rows.append({
            "POLICY_ID": pid,
            "STATE": state,
            "RISK_CLASS": risk,
            "VEHICLE_SEGMENT": vehicle,
            "EFFECTIVE_DATE": eff.date(),
            "EXPIRATION_DATE": exp.date(),
            "CANCELLATION_DATE": cancel.date() if cancel else None,
            "STATUS": status,
            "WRITTEN_PREMIUM": round(prem,2),
            "TERM_MONTHS": term
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────
# CLAIM GENERATION (TRANSACTION LEVEL)
# ─────────────────────────────────────────────────────────

def generate_claims(policies):

    rows = []
    claim_counter = 1

    for _, p in policies.iterrows():

        annual_prob = CLAIM_FREQUENCY * RISK_CLASSES[p["RISK_CLASS"]]["freq_mult"]
        exposure = p["TERM_MONTHS"] / 12

        expected_claims = annual_prob * exposure
        claim_count = np.random.poisson(expected_claims)

        for _ in range(claim_count):

            claim_id = f"CLM{claim_counter:08d}"
            claim_counter += 1

            eff = pd.to_datetime(p["EFFECTIVE_DATE"])
            exp = pd.to_datetime(p["EXPIRATION_DATE"])
            loss_date = rand_date(eff.to_pydatetime(), min(exp.to_pydatetime(), END_DATE))

            # severity trend
            years = (loss_date - START_DATE).days / 365
            ultimate = np.random.lognormal(
                mean=np.log(8000 * (1.04 ** years)),
                sigma=0.6
            )
            ultimate = round(ultimate, 2)

            # cumulative paid pattern
            cum_paid_pattern = [0.2, 0.5, 0.8, 1.0]
            dev_months = [0, 6, 12, 24]

            prev_paid = 0

            for pct, m in zip(cum_paid_pattern, dev_months):

                dev_date = loss_date + timedelta(days=30*m)

                if dev_date > END_DATE:
                    continue

                cum_paid = ultimate * pct
                incremental_paid = cum_paid - prev_paid
                prev_paid = cum_paid

                case_outstanding = ultimate - cum_paid
                incurred = cum_paid + case_outstanding

                status = "closed" if pct == 1.0 else "open"

                rows.append({
                    "CLAIM_ID": claim_id,
                    "POLICY_ID": p["POLICY_ID"],
                    "LOSS_DATE": loss_date.date() if isinstance(loss_date, datetime) else loss_date,
                    "TRANSACTION_DATE": dev_date.date() if isinstance(dev_date, datetime) else dev_date,
                    "INCREMENTAL_PAID": round(incremental_paid,2),
                    "CUMULATIVE_PAID": round(cum_paid,2),
                    "CASE_RESERVE": round(case_outstanding,2),
                    "INCURRED": round(incurred,2),
                    "STATUS": status
                })

    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────
# RATE LEVEL HISTORY
# ─────────────────────────────────────────────────────────

def generate_rate_level_history():

    rows = []
    filing_counter = 1

    # track each segment's accumlated factor
    factor_tracker = {}

    # initialize each segment to 1.0
    for state in STATES + ["ALL"]:
        for rc in list(RISK_CLASSES.keys()) + ["ALL"]:
            for vs in list(VEHICLE_SEGMENTS.keys()) + ["ALL"]:
                factor_tracker[(state, rc, vs)] = 1.0

    date = datetime(2018, 1, 1)

    while date <= END_DATE:

        # each month we have 20% chance of filing
        if random.random() < 0.20:

            state = random.choice(STATES + ["ALL"])
            risk_class = random.choice(list(RISK_CLASSES.keys()) + ["ALL"])
            vehicle_segment = random.choice(list(VEHICLE_SEGMENTS.keys()) + ["ALL"])

            change = round(random.uniform(-0.05, 0.10), 4)

            key = (state, risk_class, vehicle_segment)

            factor_tracker[key] *= (1 + change)

            rows.append({
                "FILING_ID": f"FIL{filing_counter:06d}",
                "EFFECTIVE_DATE": date.date(),
                "STATE": state,
                "RISK_CLASS": risk_class,
                "VEHICLE_SEGMENT": vehicle_segment,
                "RATE_CHANGE_PCT": change,
                "CUMULATIVE_FACTOR": round(factor_tracker[key], 6)
            })

            filing_counter += 1

        date += timedelta(days=30)

    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

def main():

    policies = generate_policies(N_POLICIES)
    claims = generate_claims(policies)
    rate_history = generate_rate_level_history()

    print("Policies:", len(policies))
    print("Claim transactions:", len(claims))
    print("Rate changes:", len(rate_history))

    policies.columns = [c.upper() for c in policies.columns]
    claims.columns   = [c.upper() for c in claims.columns]
    rate_history.columns= [c.upper() for c in rate_history.columns]

    write_pandas(conn, policies, 'POLICY')
    write_pandas(conn, claims, 'CLAIM')
    write_pandas(conn, rate_history, 'RATE_LEVEL_HISTORY')

    policies.to_csv("dim_policy.csv", index=False)
    claims.to_csv("fact_claim_transaction.csv", index=False)
    rate_history.to_csv("dim_rate_level_history.csv", index=False)

if __name__ == "__main__":
    main()
