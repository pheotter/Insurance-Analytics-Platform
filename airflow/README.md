# Airflow — Orchestration Layer

This folder contains the Airflow orchestration layer for the insurance actuarial pricing pipeline. The DAG drives end-to-end execution: data generation, dbt model runs, automated review packet exports, human-in-the-loop checkpoints, workbook uploads, and final indication outputs.

---

## Folder Structure

```text
airflow/
├── dags/
│   └── insurance_actuarial_pipeline.py   # Main DAG definition
├── review_packets/                        # Auto-generated per run
│   ├── ldf_selection/
│   ├── selected_ultimate/
│   ├── ultimate_selection/
│   ├── trend_selection/
│   └── expense_assumption/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env                                   # Snowflake credentials + Airflow vars (not committed)
```

---

## DAG: `insurance_actuarial_pipeline`

Triggered manually (`schedule=None`). Full task sequence:

| # | Task ID | What it does |
|---|---------|--------------|
| 1 | `generate_simulated_data` | Runs `generate_data.py` — creates policy, claim, and rate level data and uploads to Snowflake |
| 2 | `dbt_build_triangle_models` | Builds staging + data + triangle models (exposure, snapshots, cumulative and incremental triangles) |
| 3 | `export_triangle_for_ldf_review` | Exports a paid and reported triangle workbook to `review_packets/ldf_selection/` |
| 4 | `open_ldf_review` | Writes a review request packet; actuary updates `ldf_selection_table.xlsx` |
| 5 | `wait_for_ldf_selection_upload` | Sensor: polls until the workbook save timestamp is newer than the review open time |
| 6 | `upload_ldf_selection` | Uploads `ldf_selection_table.xlsx` back to Snowflake |
| 7 | `dbt_build_chain_ladder` | Builds LDF (raw, weighted, average, selected), CDF, and Chain Ladder ultimate models |
| 8 | `export_ultimate_for_review` | Exports Chain Ladder ultimates by segment and AY to `review_packets/selected_ultimate/` |
| 9 | `open_selected_ultimate_review` | Writes review request; actuary updates `selected_ultimate.xlsx` |
| 10 | `wait_for_selected_ultimate_upload` | Sensor: polls until workbook is saved |
| 11 | `upload_selected_ultimate` | Uploads `selected_ultimate.xlsx` to Snowflake |
| 12 | `dbt_build_ultimate_candidates` | Builds ultimate candidate models (fct_ultimate_loss, fct_ultimate_claim_count) |
| 13 | `export_ultimate_selection_for_review` | Exports all candidate methods side-by-side to `review_packets/ultimate_selection/` |
| 14 | `generate_ultimate_selection_template` | Generates a blank `ultimate_selection.xlsx` template pre-populated with segments and AYs |
| 15 | `open_ultimate_selection_review` | Writes review request; actuary picks one loss method and one claim count method per AY |
| 16 | `wait_for_ultimate_selection_upload` | Sensor: polls until workbook is saved |
| 17 | `upload_ultimate_selection` | Uploads `ultimate_selection.xlsx` to Snowflake |
| 18 | `dbt_build_selected_ultimate_metrics` | Builds selected ultimate models and frequency/severity |
| 19 | `export_frequency_severity_for_review` | Exports frequency/severity results to `review_packets/trend_selection/` |
| 20 | `open_trend_review` | Writes review request; actuary updates `trend_selection.xlsx` |
| 21 | `wait_for_trend_selection_upload` | Sensor: polls until workbook is saved |
| 22 | `upload_trend_selection` | Uploads `trend_selection.xlsx` to Snowflake |
| 23 | `dbt_build_trended_metrics` | Builds trended frequency/severity and pure premium models |
| 24 | `open_expense_review` | Writes review request; actuary updates `expense_assumption.xlsx` |
| 25 | `wait_for_expense_assumption_upload` | Sensor: polls until workbook is saved |
| 26 | `upload_expense_assumption` | Uploads `expense_assumption.xlsx` to Snowflake |
| 27 | `dbt_build_indication` | Builds `fct_indicated_premium` and `mart_indicated_rate_change_pure_premium` |
| 28 | `dbt_build_controls_summary` | Builds all 5 control and reconciliation mart models |

### Human-in-the-loop checkpoints

Each checkpoint follows the same pattern:

1. DAG exports a review workbook to `airflow/review_packets/<checkpoint>/`.
2. DAG writes a `.md` packet with run ID, workbook path, and review instructions.
3. A `PythonSensor` polls every 60 seconds (default) until the actuary saves the corresponding Excel workbook in `data_pipeline/`.
4. DAG uploads only that checkpoint's workbook back to Snowflake via `upload_actuarial_inputs.py`.

The sensor uses file modification time — not a flag file — so saving the workbook in place is all that is needed to proceed.

---

## Docker Compose Setup

### Files included

- `docker-compose.yml` — defines `postgres`, `airflow-init`, `airflow-webserver`, and `airflow-scheduler` services
- `Dockerfile` — extends the official Airflow image with project dependencies
- `requirements.txt` — Python dependencies: `dbt-core`, `dbt-snowflake`, `pandas`, `openpyxl`, `snowflake-connector-python[pandas]`, `cryptography`, `python-dotenv`
- `.env` — local credentials and Airflow variable values (see below; not committed)

The compose file mounts the entire repo into `/opt/project` inside the containers, so the DAG can reach `data_pipeline/` workbooks and write review packets to `airflow/review_packets/`.

### 1. Prepare `.env`

Create `airflow/.env`. Required values:

```env
# Snowflake credentials
SNOWFLAKE_USER=...
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_WAREHOUSE=...
SNOWFLAKE_DATABASE=...
SNOWFLAKE_SCHEMA=...
SNOWFLAKE_PRIVATE_KEY_PATH=...

# Airflow Variables (injected as AIRFLOW_VAR_* → Variable.get())
AIRFLOW_VAR_PROJECT_ROOT=/opt/project
AIRFLOW_VAR_DATA_PIPELINE_DIR=/opt/project/data_pipeline
AIRFLOW_VAR_REVIEW_PACKET_DIR=/opt/project/airflow/review_packets
AIRFLOW_VAR_SEGMENTATION_VERSION=v3
AIRFLOW_VAR_PIPELINE_PYTHON_BIN=python
AIRFLOW_VAR_DBT_BIN=dbt
AIRFLOW_VAR_REVIEW_WAIT_TIMEOUT_SECONDS=86400
AIRFLOW_VAR_REVIEW_POKE_INTERVAL_SECONDS=60
AIRFLOW_VAR_ASSUMPTION_UPLOAD_AUTHOR=airflow
AIRFLOW_VAR_ASSUMPTION_VERSION_PREFIX=airflow
```

### 2. Start Airflow

Run from the `airflow/` folder:

```bash
docker compose up airflow-init
docker compose up -d
```

Open the Airflow UI at `http://localhost:8081`.

Default credentials created by `airflow-init`:

- Username: `admin`
- Password: `admin`

### 3. Trigger the DAG

From the UI, unpause and trigger `insurance_actuarial_pipeline`, or via CLI:

```bash
docker compose exec airflow-webserver airflow dags trigger insurance_actuarial_pipeline
```

---

## Airflow Variables Reference

All variables are read with `Variable.get()` and can be overridden in the UI under **Admin → Variables** or supplied through `AIRFLOW_VAR_*` environment variables in `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `project_root` | repo root | Absolute path to the repo root inside the container |
| `data_pipeline_dir` | `<project_root>/data_pipeline` | Directory containing dbt project and Excel workbooks |
| `review_packet_dir` | `<project_root>/airflow/review_packets` | Directory where the DAG writes review request packets |
| `pipeline_python_bin` | `python` | Python interpreter used to run data scripts |
| `dbt_bin` | `dbt` | dbt executable path |
| `segmentation_version` | `v3` | Default dbt `segmentation_version` var passed to every `dbt build` |
| `review_wait_timeout_seconds` | `86400` | Max time (seconds) sensors will wait before timing out |
| `review_poke_interval_seconds` | `60` | How often sensors check the workbook modification time |
| `assumption_upload_author` | `airflow` | Author field stamped on uploaded actuarial assumption records |
| `assumption_version_prefix` | `airflow` | Prefix for the version string attached to each uploaded assumption |

---

## Supporting Scripts (in `data_pipeline/`)

These are called by the DAG as `PythonOperator` tasks:

| Script | Called by task |
|--------|---------------|
| `generate_data.py` | `generate_simulated_data` |
| `export_loss_triangles.py` | `export_triangle_for_ldf_review` |
| `export_ultimate_review.py` | `export_ultimate_for_review` |
| `export_ultimate_selection_review.py` | `export_ultimate_selection_for_review` |
| `generate_ultimate_selection_template.py` | `generate_ultimate_selection_template` |
| `export_frequency_severity_review.py` | `export_frequency_severity_for_review` |
| `upload_actuarial_inputs.py` | all `upload_*` tasks |

---

## Notes

- The DAG has `retries=1` with a 5-minute delay, so transient Snowflake or dbt errors will retry once automatically.
- Sensors run in `reschedule` mode — they release their worker slot between polls rather than holding it, which keeps resource usage low during long review windows.
- To switch Snowflake auth from environment variables to an Airflow Connection, refactor `upload_actuarial_inputs.py` and `profiles.yml` to read from the connection instead of environment variables.
