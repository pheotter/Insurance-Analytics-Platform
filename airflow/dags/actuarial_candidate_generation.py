"""Build triangle inputs and generate governed actuarial model candidates."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator


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
PYTHON_BIN = Variable.get(
    "pipeline_python_bin",
    default_var=os.getenv("PIPELINE_PYTHON_BIN", "python"),
)
DBT_BIN = Variable.get("dbt_bin", default_var=os.getenv("DBT_BIN", "dbt"))


def create_run_context(**context: Any) -> dict[str, str]:
    conf = dict(context["dag_run"].conf or {})
    as_of_date = str(conf.get("as_of_date", date.today().isoformat()))
    date.fromisoformat(as_of_date)
    return {
        "model_run_id": str(conf.get("model_run_id", uuid4())),
        "as_of_date": as_of_date,
        "triangle_grains": str(conf.get("triangle_grains", "annual")),
        "measures": str(conf.get("measures", "incurred,reported_count")),
        "development_methods": str(
            conf.get(
                "development_methods",
                "simple_average,volume_weighted,recent_3_weighted",
            )
        ),
        "tail_methods": str(conf.get("tail_methods", "none,curve")),
        "ultimate_methods": str(
            conf.get(
                "ultimate_methods",
                "chainladder,mack_chainladder,bornhuetter_ferguson,cape_cod",
            )
        ),
    }


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    result.check_returncode()


def build_triangle_inputs(**context: Any) -> None:
    run_context = context["ti"].xcom_pull(task_ids="create_run_context")
    _run(
        [
            DBT_BIN,
            "build",
            "--vars",
            json.dumps({"as_of_date": run_context["as_of_date"]}),
            "--select",
            "+int_loss_triangle_pooled",
            "+int_development_exposure",
        ],
        DATA_PIPELINE_DIR,
    )


def run_candidate_engine(**context: Any) -> None:
    run_context = context["ti"].xcom_pull(task_ids="create_run_context")
    _run(
        [
            PYTHON_BIN,
            "-m",
            "actuarial_engine.run_modeling",
            "--as-of-date",
            run_context["as_of_date"],
            "--model-run-id",
            run_context["model_run_id"],
            "--triangle-grains",
            run_context["triangle_grains"],
            "--measures",
            run_context["measures"],
            "--development-methods",
            run_context["development_methods"],
            "--tail-methods",
            run_context["tail_methods"],
            "--ultimate-methods",
            run_context["ultimate_methods"],
        ],
        PROJECT_ROOT,
    )


with DAG(
    dag_id="actuarial_candidate_generation",
    description="Build development inputs and generate model candidates.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "actuarial-platform",
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["actuarial", "chainladder", "dbt"],
) as dag:
    create_context = PythonOperator(
        task_id="create_run_context",
        python_callable=create_run_context,
    )
    dbt_inputs = PythonOperator(
        task_id="build_triangle_inputs",
        python_callable=build_triangle_inputs,
        execution_timeout=timedelta(minutes=20),
    )
    calculate_candidates = PythonOperator(
        task_id="run_actuarial_engine",
        python_callable=run_candidate_engine,
        execution_timeout=timedelta(minutes=30),
    )

    create_context >> dbt_inputs >> calculate_candidates
