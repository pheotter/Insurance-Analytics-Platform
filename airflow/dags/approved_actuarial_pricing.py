"""Build approved frequency/severity outputs for one immutable selection version."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from platform_common.snowflake import SnowflakeSettings, connect_snowflake


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(
    Variable.get("project_root", default_var=str(DEFAULT_PROJECT_ROOT))
)
DATA_PIPELINE_DIR = Path(
    Variable.get(
        "data_pipeline_dir",
        default_var=str(PROJECT_ROOT / "data_pipeline"),
    )
)
DBT_BIN = Variable.get("dbt_bin", default_var=os.getenv("DBT_BIN", "dbt"))


def _run_conf(context: dict[str, Any]) -> dict[str, str]:
    conf = dict(context["dag_run"].conf or {})
    required = ("selection_version_id", "model_run_id", "pipeline_run_id")
    missing = [key for key in required if not conf.get(key)]
    if missing:
        raise ValueError(f"Missing DAG run configuration: {', '.join(missing)}")
    UUID(str(conf["selection_version_id"]))
    UUID(str(conf["pipeline_run_id"]))
    return {key: str(conf[key]) for key in required}


def _relation(settings: SnowflakeSettings, table: str) -> str:
    return f"{settings.database}.{settings.schema}.{table}"


def validate_approved_selection(**context: Any) -> None:
    conf = _run_conf(context)
    settings = SnowflakeSettings.from_environment()
    connection = connect_snowflake(settings, autocommit=False)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {_relation(settings, 'ACTUARIAL_SELECTION_VERSION')}
                WHERE SELECTION_VERSION_ID = %s
                  AND MODEL_RUN_ID = %s
                  AND STATUS = 'APPROVED'
                """,
                (conf["selection_version_id"], conf["model_run_id"]),
            )
            if cursor.fetchone()[0] != 1:
                raise ValueError("Selection version is missing, mismatched, or not approved")
            cursor.execute(
                f"""
                UPDATE {_relation(settings, 'ACTUARIAL_PIPELINE_RUN')}
                SET STATUS = 'RUNNING', UPDATED_AT = CURRENT_TIMESTAMP()
                WHERE PIPELINE_RUN_ID = %s
                """,
                (conf["pipeline_run_id"],),
            )
            connection.commit()
        finally:
            cursor.close()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def build_approved_metrics(**context: Any) -> None:
    conf = _run_conf(context)
    variables = json.dumps(
        {
            "selection_version_id": conf["selection_version_id"],
            "loss_measure": "incurred",
        }
    )
    model_selection = [
        "+mart_indicated_rate_change_pure_premium",
        "+mart_control_tolerance_by_metric",
        "+mart_reconciliation_by_segment",
        "+mart_assumption_impact_reconciliation",
        "+mart_reserve_pricing_movement_attribution",
        "+mart_incurred_coverage",
    ]
    result = subprocess.run(
        [
            DBT_BIN,
            "build",
            "--vars",
            variables,
            "--select",
            *model_selection,
        ],
        cwd=str(DATA_PIPELINE_DIR),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    result.check_returncode()


def set_pipeline_status(status: str, **context: Any) -> None:
    conf = _run_conf(context)
    settings = SnowflakeSettings.from_environment()
    connection = connect_snowflake(settings, autocommit=False)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                UPDATE {_relation(settings, 'ACTUARIAL_PIPELINE_RUN')}
                SET STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP()
                WHERE PIPELINE_RUN_ID = %s
                """,
                (status, conf["pipeline_run_id"]),
            )
            connection.commit()
        finally:
            cursor.close()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def mark_failed(context: dict[str, Any]) -> None:
    try:
        set_pipeline_status("FAILED", **context)
    except Exception as error:
        print(f"Could not persist FAILED pipeline status: {error}")


with DAG(
    dag_id="approved_actuarial_pricing",
    description="Build pricing metrics for one approved actuarial selection version.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "actuarial-platform",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
        "on_failure_callback": mark_failed,
    },
    tags=["actuarial", "approval", "dbt"],
) as dag:
    validate_approval = PythonOperator(
        task_id="validate_approved_selection",
        python_callable=validate_approved_selection,
    )
    dbt_build = PythonOperator(
        task_id="build_approved_frequency_severity",
        python_callable=build_approved_metrics,
        execution_timeout=timedelta(minutes=20),
    )
    mark_success = PythonOperator(
        task_id="mark_pipeline_succeeded",
        python_callable=set_pipeline_status,
        op_kwargs={"status": "SUCCEEDED"},
    )

    validate_approval >> dbt_build >> mark_success
