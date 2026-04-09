# Data Pipeline

This folder contains the dbt project, Python data-loading scripts, and actuarial input workbooks used by the insurance pricing pipeline.

## Main components

- `generate_data.py`
  Simulates policy, claim, and rate level history data and uploads them to Snowflake.
- `upload_actuarial_inputs.py`
  Uploads one or more actuarial workbook inputs into Snowflake source tables.
- `models/`
  dbt models for staging, intermediate actuarial logic, and marts.
- `*.xlsx`
  Human-reviewed actuarial input workbooks.

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
  Stores expense assumptions by state.

## Ultimate selection flow

The ultimate workflow now has two layers:

1. `selected_ultimate.xlsx`
   Upload candidate ultimate values for methods such as `BF`, `Cape_cod`, and `Judgements`.
2. `ultimate_selection.xlsx`
   Choose which method should apply for each `accident_year`, separately for:
   - `loss`
   - `claim_count`

dbt then builds:

- [fct_ultimate_loss.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/fct_ultimate_loss.sql)
- [fct_ultimate_claim_count.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/fct_ultimate_claim_count.sql)
- [fct_selected_ultimate_loss.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/fct_selected_ultimate_loss.sql)
- [fct_selected_ultimate_claim_count.sql](/D:/internship/airflow/dbt_project/data_pipeline/models/marts/fct_selected_ultimate_claim_count.sql)

## Helpful scripts

- Upload all workbook inputs:
```bash
python upload_actuarial_inputs.py
```

- Upload a single workbook:
```bash
python upload_actuarial_inputs.py --file trend_selection.xlsx
```

- Generate the ultimate selection template:
```bash
python generate_ultimate_selection_template.py --segmentation-version v3 --output ultimate_selection.xlsx
```

- Export all ultimate candidates for review:
```bash
python export_ultimate_selection_review.py --output ../airflow/review_packets/ultimate_selection/review.xlsx
```

## Recommended dbt run patterns

- Build the pricing output chain:
```bash
dbt run --select fct_frequency_severity+
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
- Current indication outputs are built from:
  - selected ultimate loss / claim count
  - frequency / severity
  - trended frequency / severity
  - pure premium
  - indicated premium / rate change
