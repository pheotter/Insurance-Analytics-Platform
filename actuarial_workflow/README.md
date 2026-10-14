# Actuarial Selection Workflow

This package adds a governed human-in-the-loop workflow around the candidate
results produced by `actuarial_engine`.

## Boundaries

```text
actuarial_engine    Pure candidate calculations
actuarial_workflow  Selection, approval, audit, and Airflow application rules
actuarial_api       FastAPI HTTP delivery layer
streamlit_app       Replaceable MVP presentation layer
Snowflake           Candidate, selection, audit, and approved analytical data
Airflow/dbt         Approved downstream frequency/severity execution
```

The Streamlit app never writes directly to Snowflake. Both Streamlit and a
future React UI use the same FastAPI contract, while workflow rules remain in
the service layer.

## Install

From the repository root:

```bash
python -m pip install -e '.[workflow,test]'
```

Export the Snowflake variables listed in `actuarial_api/.env.example`. For a
local UI demonstration, leave `AIRFLOW_TRIGGER_ENABLED=false`; an approval is
still recorded and its pipeline status is saved as `DISABLED`.

## Initialize Snowflake tables

The actuarial candidate output tables must already exist. Create the new
workflow tables with:

```bash
python -m actuarial_workflow.cli init-schema
```

## Run

Terminal 1:

```bash
bash scripts/run_actuarial_api.sh
```

Terminal 2:

```bash
bash scripts/run_streamlit.sh
```

Open `http://localhost:8501`. FastAPI documentation is available at
`http://localhost:8000/docs`.

The MVP identity headers (`X-Actuarial-User` and `X-Actuarial-Role`) are a
trusted-demo boundary, not production authentication. Replace them with OIDC
claims before exposing the service outside a local or controlled environment.

## Workflow

1. Run `actuarial_engine` with both `incurred` and `reported_count` measures.
2. Create a draft tied to the immutable `model_run_id`.
3. Select one consistent development pattern, one tail, and ultimate methods.
4. Submit the version for review.
5. A different reviewer approves or rejects it.
6. Approval creates a pipeline record and triggers `approved_actuarial_pricing`.
7. The DAG validates approval and runs dbt with the exact
   `selection_version_id`.

Approved versions cannot be edited. Create a new draft version for any change.
If the Airflow request fails after approval, a reviewer can retry with
`POST /api/v1/selection-versions/{id}/trigger`; approval is not repeated.
