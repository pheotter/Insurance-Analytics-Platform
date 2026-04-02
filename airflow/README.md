# Airflow Setup

This folder contains the orchestration layer for the actuarial dbt pipeline.

## What the DAG does

The DAG at `airflow/dags/insurance_actuarial_pipeline.py` runs this flow:

1. Generate simulated base data and upload it to Snowflake.
2. Run the dbt models needed to build the triangle and LDF candidates.
3. Export a review workbook with cumulative paid and cumulative reported triangles.
4. Pause for actuarial workbook updates.
5. Export an ultimate review workbook by segment and accident year.
6. Export a frequency/severity review workbook by segment and accident year.
7. Upload each reviewed workbook back to Snowflake.
8. Continue dbt runs until final indication outputs are built.

Each manual checkpoint creates a small review packet under `airflow/review_packets/`.
The corresponding sensor waits until the workbook file has been saved again.

## Docker Compose run

Files included:

- `docker-compose.yml`
- `Dockerfile`
- `requirements.txt`
- `.env.example`

### 1. Prepare the environment file

Copy `.env.example` to `.env`, then fill in your Snowflake values.

Important values:

- `SNOWFLAKE_*`: credentials and warehouse/database/schema settings
- `AIRFLOW_VAR_PROJECT_ROOT`: the repo path inside the container
- `AIRFLOW_VAR_DATA_PIPELINE_DIR`: where dbt and the Excel workbooks live
- `AIRFLOW_VAR_REVIEW_PACKET_DIR`: where Airflow writes review requests
- `AIRFLOW_VAR_SEGMENTATION_VERSION`: default dbt var for the DAG

### 2. Start Airflow

Run these commands from the `airflow/` folder:

```bash
docker compose up airflow-init
docker compose up -d
```

Open Airflow at `http://localhost:8081`.

Default local credentials from the init service:

- username: `admin`
- password: `admin`

### 3. Trigger the DAG

From the UI or with CLI:

```bash
docker compose exec airflow-webserver airflow dags trigger insurance_actuarial_pipeline
```

## Airflow Variables used by the DAG

The DAG no longer hardcodes repo paths. It reads these Variables:

- `project_root`
- `data_pipeline_dir`
- `review_packet_dir`
- `pipeline_python_bin`
- `dbt_bin`
- `segmentation_version`
- `review_wait_timeout_seconds`
- `review_poke_interval_seconds`

In Docker Compose, these are supplied through environment-backed Variables using names like `AIRFLOW_VAR_PROJECT_ROOT`.

## Notes

- The compose file mounts the whole repo into `/opt/project`.
- The DAG still expects your Excel workbooks to be edited in the mounted project directory.
- If you later want to move Snowflake auth from environment variables into an Airflow Connection, the next step would be refactoring the Python upload scripts and dbt profile to read from that connection instead.
