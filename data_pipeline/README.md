# Data Pipeline

This folder contains the dbt project, Python data-loading scripts, workbook utilities, and actuarial input workbooks used by the insurance pricing pipeline.

## Main components

- `generate_data.py`
  Simulates policy, claim, and rate level history data and uploads them to Snowflake.
- `upload_actuarial_inputs.py`
  Uploads one or more actuarial workbook inputs into Snowflake source tables.
- `models/`
  dbt models for staging, intermediate actuarial logic, marts, and controls.
- `*.xlsx`
  Human-reviewed actuarial input workbooks.

## dbt model layout

- `models/staging/`
  Source cleanup, schema normalization, and workbook input staging.
- `models/intermediate/data/`
  Claim snapshots and policy exposure.
- `models/intermediate/triangle/`
  Cumulative and incremental triangles.
- `models/intermediate/ldf/`
  Raw, weighted, average, and selected LDF logic.
- `models/intermediate/cdf/`
  CDF derivation from selected LDFs.
- `models/intermediate/ultimate/`
  Chain Ladder ultimate outputs.
- `models/marts/ultimate/`
  Candidate and selected ultimate outputs.
- `models/marts/frequency_severity/`
  Frequency and severity outputs.
- `models/marts/pure_premium/`
  Trended metrics and pure premium outputs.
- `models/marts/indicated_premium/`
  Indicated premium and indicated rate change outputs.
- `models/marts/controls/`
  Reconciliation, tolerance, and attribution summaries.

## Workbook roles

- `ldf_selection_table.xlsx`
  Selects LDF assumptions by segmentation and development.
- `selected_ultimate.xlsx`
  Stores candidate ultimate values by method, accident year, type, and segment.
- `ultimate_selection.xlsx`
  Stores the final selected method for each accident year.
  This workbook does not hold the final ultimate amount directly; it tells dbt which method to use for each AY.
- `trend_selection.xlsx`
  Stores frequency and severity trend assumptions.
- `expense_assumption.xlsx`
  Stores expense assumptions by pricing version and state.

## Ultimate selection flow

The ultimate workflow now has two layers:

1. `selected_ultimate.xlsx`
   Upload candidate ultimate values for methods such as `BF`, `Cape_cod`, and `Judgements`.
2. `ultimate_selection.xlsx`
   Choose which method should apply for each `accident_year`, separately for:
   - `loss`
   - `claim_count`

dbt then builds:

- [fct_ultimate_loss.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/ultimate/fct_ultimate_loss.sql)
- [fct_ultimate_claim_count.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/ultimate/fct_ultimate_claim_count.sql)
- [fct_selected_ultimate_loss.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/ultimate/fct_selected_ultimate_loss.sql)
- [fct_selected_ultimate_claim_count.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/ultimate/fct_selected_ultimate_claim_count.sql)

## Helpful scripts

- Upload all workbook inputs:
```bash
python upload_actuarial_inputs.py
```

- Upload a single workbook:
```bash
python upload_actuarial_inputs.py --file trend_selection.xlsx
```

- Upload with governance metadata:
```bash
python upload_actuarial_inputs.py --file trend_selection.xlsx --author Alyssa --comment "Updated severity trend after review" --version trend_v2
```

The upload script now also:

- writes a version row into `ASSUMPTION_VERSION`
- writes field-level and row-level diffs into `ASSUMPTION_CHANGE_LOG`
- registers Airflow context into `PIPELINE_RUN_METADATA`
- saves a readable markdown diff report into `data_pipeline/governance_reports/`

- Generate the ultimate selection template:
```bash
python generate_ultimate_selection_template.py --segmentation-version v3 --output ultimate_selection.xlsx
```

- Export all ultimate candidates for review:
```bash
python export_ultimate_selection_review.py --output ../airflow/review_packets/ultimate_selection/review.xlsx
```

## Recommended dbt run patterns

- Build the selected-ultimate to pricing chain:
```bash
dbt run --select fct_selected_ultimate_loss fct_selected_ultimate_claim_count fct_frequency_severity fct_frequency_severity_trended fct_pure_premium fct_indicated_premium mart_indicated_rate_change_pure_premium
```

- Build the controls layer:
```bash
dbt run --select mart_control_totals_financial_summary mart_control_tolerance_by_metric mart_reconciliation_by_segment mart_assumption_impact_reconciliation mart_reserve_pricing_movement_attribution
```

- Important note:
  `mart_reserve_pricing_movement_attribution` depends on `mart_assumption_impact_reconciliation`, so it should be selected together with that model unless the dependency has already been built in the target schema.

## dbt notes

- `segmentation_version` is controlled through dbt vars and Airflow Variables.
- Expense assumptions are state-level only.
- Expense assumptions are versioned by `pricing_version` and segmented by state.
- Uploading workbook inputs now also writes governance metadata into:
  - `ASSUMPTION_VERSION`
  - `ASSUMPTION_CHANGE_LOG`
  - `PIPELINE_RUN_METADATA`
- Current indication outputs are built from:
  - selected ultimate loss / claim count
  - frequency / severity
  - trended frequency / severity
  - pure premium
  - indicated premium / rate change

## Marts-layer validation notes

Most hard validation rules currently live in source, staging, and intermediate layers. The marts layer currently has stronger diagnostics than direct tests, mainly through:

- control marts
- reconciliation rollups
- output comparison tables
