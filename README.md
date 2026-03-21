# Insurance Analytics Platform

A personal project focused on **auto insurance actuarial pricing**, using **Snowflake + dbt + Python** to build a reproducible workflow from data generation and loss triangles to LDF/CDF, ultimate estimates, frequency/severity, and indicated premium.

> This repository is currently a portfolio-grade implementation designed to demonstrate actuarial workflow thinking and data pipeline design, with an Airflow automation plan for human-in-the-loop operations.

---

## 1) Project Objectives

- Build a repeatable actuarial pricing data pipeline.
- Turn actuarial judgment inputs (LDF selection, selected ultimate, trend, expense assumptions) into structured data assets.
- Support multiple segmentation strategies (segmentation versions) for comparison.
- Produce key pricing outputs used for rate indication:
  - Ultimate loss / claim count
  - Frequency / Severity
  - Pure Premium
  - Indicated Premium / Indicated Rate Change

---

## 2) Tech Stack

- **Data warehouse**: Snowflake
- **Transformation framework**: dbt
- **Data simulation**: Python (pandas / numpy)
- **(Planned) orchestration**: Airflow

---

## 3) Repository Structure

```text
.
├── README.md
├── data_pipeline/
│   ├── generate_data.py                # Simulates policy/claim/rate history and writes to Snowflake
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── macros/
│   │   ├── effective_date_valid.sql
│   │   ├── generate_years.sql
│   │   └── segmentation.sql
│   └── models/
│       ├── staging/                    # Source cleanup and column standardization
│       ├── intermediate/               # Exposure, triangle, LDF/CDF, ultimate
│       ├── marts/                      # Frequency/severity, premium, rate change
│       ├── dim/
│       └── config/
└── *.xlsx                              # Actuarial input templates (LDF / trend / selected ultimate / expense)
```

---

## 4) Current Data Flow

1. `generate_data.py` creates and uploads:
   - `policy`
   - `claim` (transaction-level development)
   - `rate_level_history`
2. dbt `staging`: source mapping and column cleanup.
3. dbt `intermediate`:
   - claim snapshot and cumulative triangle
   - LDF/CDF derivation
   - Chain Ladder ultimate
   - policy exposure
4. dbt `marts`:
   - selected ultimate by method
   - frequency / severity (with trend)
   - pure premium
   - indicated premium / rate change

---

## 5) Human-in-the-Loop Actuarial Checkpoints

The workflow supports actuarial judgment updates at these checkpoints:

1. **LDF selection**: update `ldf_selection_table`
2. **Ultimate selection**: update `selected_ultimate`
3. **Trend selection**: update `trend_selection`
4. **Expense assumptions**: update `expense_assumption`

This design keeps both:
- reproducible pipeline execution
- expert judgment flexibility

---

## 6) Quick Start

### 6.1 Requirements

- Python 3.10+
- dbt-core + dbt-snowflake
- Snowflake account and key-based auth

### 6.2 Configure Snowflake connection for Python data generation

Set these environment variables:

```bash
export SNOWFLAKE_USER=...
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_WAREHOUSE=...
export SNOWFLAKE_DATABASE=...
export SNOWFLAKE_SCHEMA=...
export SNOWFLAKE_PRIVATE_KEY_PATH=...
```

### 6.3 Generate and upload simulated data

```bash
python generate_data.py
```

### 6.4 Run dbt

```bash
cd data_pipeline

# install packages
dbt deps

# build + test
dbt build
```

You can also control method selection with vars (adjust to your model settings):

```bash
dbt run --vars '{segmentation_version: v1, loss_method: Chain_ladder, claim_count_method: Chain_ladder}'
```

---

## 7) Planned Airflow Automation

Goal: orchestrate the full `dbt + actuarial review + upload + dbt` cycle with auditability.

DAG stages:

1. `dbt_build_triangle`
2. `export_triangle_for_actuary`
3. `wait_for_ldf_selection_upload`
4. `dbt_run_chain_ladder`
5. `wait_for_selected_ultimate_upload`
6. `dbt_run_with_method_vars`
7. `wait_for_trend_selection_upload`
8. `dbt_run_trended_metrics`
9. `wait_for_expense_assumption_upload`
10. `dbt_run_indication`

Metadata for each manual upload:
- `run_id`
- `uploaded_at`
- `uploaded_by`
- `is_approved`

This makes Airflow sensors robust and traceable.

---

## 8) Gaps and Next Steps

- Some SQL models still need naming and syntax consistency cleanup.
- Data quality coverage can be expanded (null/range/relationship/freshness tests).
- A visualization layer (e.g., Streamlit/BI) can be added for indication and sensitivity analysis.
- A future version can extend to cyber insurance features (security controls / threat exposure).

---

## 9) Skills Demonstrated

- SQL / dbt modeling
- Actuarial pricing workflow design (triangle, LDF/CDF, ultimate, indication)
- Human-in-the-loop process integration
- Data pipeline architecture with orchestration readiness

---

## 10) License

This project is for portfolio/demo purposes.
