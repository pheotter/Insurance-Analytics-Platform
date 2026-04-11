# Insurance Analytics Platform

A personal project focused on **auto insurance actuarial pricing**, using **Snowflake + dbt + Python** to build a reproducible workflow from simulated source data through triangles, LDF/CDF, ultimate candidates, selected ultimate methods, trend review, indication outputs, and a controls layer.

> This repository is a portfolio-grade implementation of a human-in-the-loop actuarial workflow with Airflow orchestration.

---

## 1) Project Objectives

- Build a repeatable actuarial pricing data pipeline.
- Turn actuarial judgment inputs into structured data assets instead of ad hoc spreadsheet logic.
- Support multiple segmentation strategies through `segmentation_version`.
- Produce key pricing outputs used for indication:
  - ultimate loss / claim count
  - frequency / severity
  - pure premium
  - indicated premium / indicated rate change
- Add a controls layer for reconciliation, tolerances, and movement attribution.

---

## 2) Tech Stack

- **Data warehouse**: Snowflake
- **Transformation framework**: dbt
- **Data simulation and workbook utilities**: Python
- **Orchestration**: Airflow

---

## 3) Repository Structure

```text
.
├── README.md
├── airflow/
└── data_pipeline/
    ├── generate_data.py                # Simulates policy/claim/rate history and writes to Snowflake
    ├── dbt_project.yml
    ├── profiles.yml
    ├── macros/
    ├── models/
    │   ├── staging/                    # Source cleanup and column standardization
    │   ├── intermediate/
    │   │   ├── data/
    │   │   ├── triangle/
    │   │   ├── ldf/
    │   │   ├── cdf/
    │   │   └── ultimate/
    │   ├── marts/
    │   │   ├── ultimate/
    │   │   ├── frequency_severity/
    │   │   ├── pure_premium/
    │   │   ├── indicated_premium/
    │   │   └── controls/
    │   ├── dim/
    │   └── config/
    └── *.xlsx                          # Actuarial input templates (LDF / trend / selected ultimate / expense)
```

Workbook templates in `data_pipeline/` include:

- `ldf_selection_table.xlsx`
- `selected_ultimate.xlsx`
- `ultimate_selection.xlsx`
- `trend_selection.xlsx`
- `expense_assumption.xlsx`

---

## 4) Current Data Flow

1. `generate_data.py` creates and uploads:
   - `policy`
   - `claim` (transaction-level development)
   - `rate_level_history`
2. dbt `staging`: source mapping and column cleanup.
3. dbt `intermediate`:
   - `data/`: claim snapshots and policy exposure
   - `triangle/`: cumulative and incremental triangles
   - `ldf/`: raw, weighted, average, and selected LDF logic
   - `cdf/`: development-to-ultimate conversion factors
   - `ultimate/`: Chain Ladder ultimate outputs
4. dbt `marts`:
   - `ultimate/`: all candidate and selected ultimate outputs
   - `frequency_severity/`: frequency and severity metrics
   - `pure_premium/`: trended metrics and pure premium outputs
   - `indicated_premium/`: indicated premium and rate change outputs
   - `controls/`: reconciliation, tolerance, and attribution summaries

---

## 5) Human-in-the-Loop Actuarial Checkpoints

The workflow supports actuarial judgment updates at these checkpoints:

1. **LDF selection**: update `ldf_selection_table.xlsx`
2. **Candidate ultimate input**: update `selected_ultimate.xlsx`
3. **Final ultimate method selection by AY**: update `ultimate_selection.xlsx`
4. **Trend selection**: update `trend_selection.xlsx`
5. **Expense assumptions**: update `expense_assumption.xlsx`

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
dbt deps
dbt build
```

You can also run dbt manually with segmentation vars:

```bash
dbt run --vars '{segmentation_version: v1}'
```

---

## 7) Airflow Automation

The project includes an Airflow DAG at `airflow/dags/insurance_actuarial_pipeline.py`.

It orchestrates:

1. `generate_simulated_data`
2. `dbt_build_triangle_models`
3. `export_triangle_for_ldf_review`
4. `open_ldf_review`
5. `wait_for_ldf_selection_upload`
6. `upload_ldf_selection`
7. `dbt_build_chain_ladder`
8. `export_ultimate_for_review`
9. `open_selected_ultimate_review`
10. `wait_for_selected_ultimate_upload`
11. `upload_selected_ultimate`
12. `dbt_build_ultimate_candidates`
13. `export_ultimate_selection_for_review`
14. `generate_ultimate_selection_template`
15. `open_ultimate_selection_review`
16. `wait_for_ultimate_selection_upload`
17. `upload_ultimate_selection`
18. `dbt_build_selected_ultimate_metrics`
19. `export_frequency_severity_for_review`
20. `open_trend_review`
21. `wait_for_trend_selection_upload`
22. `upload_trend_selection`
23. `dbt_build_trended_metrics`
24. `open_expense_review`
25. `wait_for_expense_assumption_upload`
26. `upload_expense_assumption`
27. `dbt_build_indication`
28. `dbt_build_controls_summary`

How the manual checkpoints work:

- Airflow writes a review packet into `airflow/review_packets/`
- You update the corresponding Excel workbook in `data_pipeline/`
- The sensor continues only after the workbook modification time is newer than the checkpoint open time
- The DAG uploads only the workbook for that checkpoint back to Snowflake

Supporting scripts:

- `data_pipeline/upload_actuarial_inputs.py`
- `data_pipeline/export_ultimate_selection_review.py`
- `data_pipeline/generate_ultimate_selection_template.py`

Airflow setup notes:

- A Docker Compose startup environment is included under `airflow/`
- The DAG reads paths and runtime settings from Airflow Variables
- Docker injects those Variables through `AIRFLOW_VAR_*` environment variables
- Snowflake environment variables must be present in `airflow/.env`

---

## 8) Controls Layer

In addition to dbt tests, the project includes a controls and reconciliation layer implemented as dbt marts. These models are meant to explain differences, quantify impacts, and support exception reporting rather than just returning pass/fail results.

- `mart_control_totals_financial_summary`
  Summarizes key source-versus-target control totals such as premium, exposure, paid, incurred, and claim count.
- `mart_control_tolerance_by_metric`
  Applies metric-specific tolerances and classifies each control as `PASS`, `WARN`, or `FAIL`.
- `mart_reconciliation_by_segment`
  Breaks reconciliation results down by segment to help isolate where differences are coming from.
- `mart_assumption_impact_reconciliation`
  Compares selected actuarial assumptions against Chain Ladder baselines to show assumption-driven impacts.
- `mart_reserve_pricing_movement_attribution`
  Separates movement into reserve-method impact, trend impact, and expense/profit impact to support result explainability.

These models complement the dbt test suite:

- dbt tests are used for rule enforcement and pass/fail validation
- control marts are used for diagnostics, explanation, and future dashboarding / monitoring

At the moment, the `marts` layer has stronger diagnostics than direct tests. Most hard validation rules still live in source, staging, and intermediate models, while the marts layer is currently checked mainly through:

- control marts
- reconciliation rollups
- downstream business-rule tests that validate outputs indirectly

---

## 9) Next Steps

The next set of improvements for this platform would focus on making it more production-oriented and more actuarially robust:

1. **Results consumption layer**
   - Add a lightweight UI or dashboard for review and analysis
   - Show triangle review pages
   - Compare ultimate candidates across methods
   - Summarize selected methods by accident year
   - Add trend review charts
   - Add pure premium and indication waterfall views
   - Support segmentation comparison

2. **Broader actuarial method support**
   - Expand BF decomposition
   - Make Cape Cod implementation more explicit
   - Add paid-versus-reported comparison
   - Add tail factor logic
   - Add clearer selection diagnostics
   - Support calendar-effect and exposure-trend splits
   - Support scenario comparison across methods
   - Support valuation date with monthly or quarterly
   - Incorportate [chainladder-python] package(https://chainladder-python.readthedocs.io/en/latest/intro.html)
   - Add tail factor

3. **More production-grade engineering**
   - Add a REST API layer for assumptions and results
   - Add a FastAPI service layer
   - Improve containerization and deployment setup
   - Add CI/CD checks
   - Add monitoring and alerting
   - Add role-based access design
   - Add logging and audit trails

---

## 10) Skills Demonstrated

- SQL / dbt modeling
- Actuarial pricing workflow design
- Human-in-the-loop process integration
- Data pipeline architecture with orchestration readiness
- Reconciliation and controls design

---

## 11) License

This project is for portfolio/demo purposes.
