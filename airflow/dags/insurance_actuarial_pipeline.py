from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_path_variable(name, default_value):
    return Path(Variable.get(name, default_var=str(default_value)))


PROJECT_ROOT = get_path_variable("project_root", DEFAULT_PROJECT_ROOT)
DATA_PIPELINE_DIR = get_path_variable("data_pipeline_dir", PROJECT_ROOT / "data_pipeline")
REVIEW_PACKET_DIR = get_path_variable("review_packet_dir", PROJECT_ROOT / "airflow" / "review_packets")

PYTHON_BIN = Variable.get("pipeline_python_bin", default_var=os.getenv("PIPELINE_PYTHON_BIN", "python"))
DBT_BIN = Variable.get("dbt_bin", default_var=os.getenv("DBT_BIN", "dbt"))
DEFAULT_SEGMENTATION_VERSION = Variable.get("segmentation_version", default_var="v3")
WAIT_TIMEOUT_SECONDS = int(Variable.get("review_wait_timeout_seconds", default_var=str(60))) #60 * 60 * 24
WAIT_POKE_INTERVAL_SECONDS = int(Variable.get("review_poke_interval_seconds", default_var="60"))
ASSUMPTION_UPLOAD_AUTHOR = Variable.get(
    "assumption_upload_author",
    default_var=os.getenv("ASSUMPTION_AUTHOR", "airflow"),
)
ASSUMPTION_VERSION_PREFIX = Variable.get(
    "assumption_version_prefix",
    default_var=os.getenv("ASSUMPTION_VERSION_PREFIX", "airflow"),
)
ALERT_EMAILS = Variable.get(
    "alert_emails",
    default_var=os.getenv("ALERT_EMAIL", None)
).split(",")

TRIANGLE_BUILD_MODELS = [
    "segmentation_config",
    "dim_date",
    "dim_valuation_dates",
    "stg_policy",
    "stg_claim",
    "stg_rate_level_history",
    "int_claim_snapshot",
    "int_policy_exposure",
    "int_claim_triangle_cumulative",
    "int_claim_triangle_incremental",
]

CHAIN_LADDER_MODELS = [
    "stg_ldf_selection_table_incurred",
    "stg_ldf_selection_table_claim_count",
    "stg_ldf_selection_table_paid",
    "int_ldf_raw",
    "int_ldf_last3_weighted",
    "int_ldf_avg_incurred",
    "int_ldf_avg_claim_count",
    "int_ldf_avg_paid",
    "int_ldf_weighted_incurred",
    "int_ldf_weighted_claim_count",
    "int_ldf_weighted_paid",
    "int_ldf_selected_incurred",
    "int_ldf_selected_claim_count",
    "int_ldf_selected_paid",
    "int_cdf_incurred",
    "int_cdf_claim_count",
    "int_cdf_paid",
    "int_ultimate_incurred_CL",
    "int_ultimate_claim_count_CL",
    "int_ultimate_paid_CL",
]

ULTIMATE_CANDIDATE_MODELS = [
    "stg_selected_ultimate_loss",
    "stg_selected_ultimate_claim_count",
    "fct_ultimate_loss",
    "fct_ultimate_claim_count",
]

SELECTED_ULTIMATE_METRICS_MODELS = [
    "stg_ultimate_selection_loss",
    "stg_ultimate_selection_claim_count",
    "fct_selected_ultimate_loss",
    "fct_selected_ultimate_claim_count",
    "fct_frequency_severity",
]

TRENDED_METRICS_MODELS = [
    "stg_trend_selection",
    "fct_frequency_severity_trended",
    "fct_pure_premium",
]

INDICATION_MODELS = [
    "stg_expense_assumption",
    "fct_indicated_premium",
    "mart_indicated_rate_change_pure_premium",
]

CONTROL_SUMMARY_MODELS = [
    "mart_control_totals_financial_summary",
    "mart_control_tolerance_by_metric",
    "mart_reconciliation_by_segment",
    "mart_assumption_impact_reconciliation",
    "mart_reserve_pricing_movement_attribution",
]

# -----------------------
# Helpers
# -----------------------

def run_command(command, cwd):
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


def run_python_script(script_name, script_args=None):
    command = [PYTHON_BIN, script_name]
    if script_args:
        command.extend(script_args)
    run_command(command, DATA_PIPELINE_DIR)

def run_dbt_build(model_names):
    run_command(
        [
            DBT_BIN,
            "build",
            "--vars",
            f"{{segmentation_version: {DEFAULT_SEGMENTATION_VERSION}}}",
            "--select",
            *model_names,
        ],
        DATA_PIPELINE_DIR,
    )

# -----------------------
# Human-in-the-loop
# -----------------------

def create_review_request(checkpoint_name, workbook_name, instructions, **context):
    checkpoint_dir = REVIEW_PACKET_DIR / checkpoint_name
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    ready_at = datetime.now(timezone.utc)
    ready_at_iso = ready_at.isoformat()
    dag_run_id = context["dag_run"].run_id

    packet_path = checkpoint_dir / f"{dag_run_id}.md"
    packet_path.write_text(
        "\n".join(
            [
                f"# {checkpoint_name}",
                "",
                f"- Run ID: {dag_run_id}",
                f"- Workbook to update: {DATA_PIPELINE_DIR / workbook_name}",
                f"- Ready at (UTC): {ready_at_iso}",
                "",
                instructions,
                "",
                "After saving the workbook, let the Airflow sensor continue automatically.",
            ]
        ),
        encoding="utf-8",
    )

    return ready_at_iso


def workbook_was_updated(workbook_name, ready_at, **_context):
    workbook_path = DATA_PIPELINE_DIR / workbook_name
    if not workbook_path.exists():
        return False

    modified_at = datetime.fromtimestamp(workbook_path.stat().st_mtime, tz=timezone.utc)
    ready_at_dt = datetime.fromisoformat(ready_at)
    return modified_at >= ready_at_dt


def sensor_kwargs(workbook_name, upstream_task_id):
    return {
        "python_callable": workbook_was_updated,
        "op_kwargs": {
            "workbook_name": workbook_name,
            "ready_at": f"{{{{ ti.xcom_pull(task_ids='{upstream_task_id}') }}}}",
        },
        "mode": "reschedule",
        "poke_interval": WAIT_POKE_INTERVAL_SECONDS,
        "timeout": WAIT_TIMEOUT_SECONDS,
    }


def build_upload_script_args(file_name, checkpoint_name):
    return [
        "--file",
        file_name,
        "--author",
        ASSUMPTION_UPLOAD_AUTHOR,
        "--comment",
        f"Airflow upload from {checkpoint_name} checkpoint for run {{{{ run_id }}}}",
        "--version",
        f"{ASSUMPTION_VERSION_PREFIX}_{checkpoint_name}_{{{{ run_id }}}}",
    ]

# -----------------------
# DAG
# -----------------------

default_args = {
    "owner": "yy",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ALERT_EMAILS,
}


with DAG(
    dag_id="insurance_actuarial_pipeline",
    description="Human-in-the-loop actuarial pricing pipeline orchestrated with Airflow and dbt.",
    default_args=default_args,
    start_date=datetime(2026, 4, 9),
    schedule=None,
    catchup=False,
    tags=["dbt", "snowflake", "actuarial"],
) as dag:

    # -----------------------
    # Data generation
    # -----------------------

    generate_simulated_data = PythonOperator(
        task_id="generate_simulated_data",
        python_callable=run_python_script,
        op_kwargs={"script_name": "generate_data.py"},
    )

    # -----------------------
    # Triangle build (includes staging + data)
    # -----------------------

    dbt_build_triangle_models = PythonOperator(
        task_id="dbt_build_triangle_models",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": TRIANGLE_BUILD_MODELS},
        execution_timeout=timedelta(minutes=15),
    )

    # -----------------------
    # LDF review
    # -----------------------

    export_triangle_for_ldf_review = PythonOperator(
        task_id="export_triangle_for_ldf_review",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "export_loss_triangles.py",
            "script_args": [
                "--segmentation-version",
                DEFAULT_SEGMENTATION_VERSION,
                "--output",
                str(REVIEW_PACKET_DIR / "ldf_selection" / "{{ run_id }}_loss_triangles.xlsx"),
            ],
        },
    )

    open_ldf_review = PythonOperator(
        task_id="open_ldf_review",
        python_callable=create_review_request,
        op_kwargs={
            "checkpoint_name": "ldf_selection",
            "workbook_name": "ldf_selection_table.xlsx",
            "instructions": (
                "Review the exported triangle workbook at "
                + str(REVIEW_PACKET_DIR / "ldf_selection" / "{{ run_id }}_loss_triangles.xlsx")
                + ", then update the selected LDF workbook, "
                "and save the file in place."
            ),
        },
    )

    wait_for_ldf_selection_upload = PythonSensor(
        task_id="wait_for_ldf_selection_upload",
        retries=0,
        **sensor_kwargs("ldf_selection_table.xlsx", "open_ldf_review"),
    )

    upload_ldf_selection = PythonOperator(
        task_id="upload_ldf_selection",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "upload_actuarial_inputs.py",
            "script_args": build_upload_script_args("ldf_selection_table.xlsx", "ldf_selection"),
        },
    )

    # ------------------------------------
    # Chain ladder (ldf + cdf + ultimate)
    # ------------------------------------

    dbt_build_chain_ladder = PythonOperator(
        task_id="dbt_build_chain_ladder",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": CHAIN_LADDER_MODELS},
        execution_timeout=timedelta(minutes=20),
    )

    export_ultimate_for_review = PythonOperator(
        task_id="export_ultimate_for_review",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "export_ultimate_review.py",
            "script_args": [
                "--output",
                str(REVIEW_PACKET_DIR / "selected_ultimate" / "{{ run_id }}_ultimate_review.xlsx"),
            ],
        },
    )

    open_selected_ultimate_review = PythonOperator(
        task_id="open_selected_ultimate_review",
        python_callable=create_review_request,
        op_kwargs={
            "checkpoint_name": "selected_ultimate",
            "workbook_name": "selected_ultimate.xlsx",
            "instructions": (
                "Review the exported ultimate workbook at "
                + str(REVIEW_PACKET_DIR / "selected_ultimate" / "{{ run_id }}_ultimate_review.xlsx")
                + ", then update selected ultimates for loss "
                "and claim count, and save the workbook."
            ),
        },
    )

    wait_for_selected_ultimate_upload = PythonSensor(
        task_id="wait_for_selected_ultimate_upload",
        retries=0,
        **sensor_kwargs("selected_ultimate.xlsx", "open_selected_ultimate_review"),
    )

    upload_selected_ultimate = PythonOperator(
        task_id="upload_selected_ultimate",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "upload_actuarial_inputs.py",
            "script_args": build_upload_script_args("selected_ultimate.xlsx", "selected_ultimate"),
        },
    )

    # ---------------------------------------------------------
    # Ultimate loss & ultimate claim counts of Several Methods
    # ---------------------------------------------------------

    dbt_build_ultimate_candidates = PythonOperator(
        task_id="dbt_build_ultimate_candidates",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": ULTIMATE_CANDIDATE_MODELS},
        execution_timeout=timedelta(minutes=15),
    )

    export_ultimate_selection_for_review = PythonOperator(
        task_id="export_ultimate_selection_for_review",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "export_ultimate_selection_review.py",
            "script_args": [
                "--output",
                str(REVIEW_PACKET_DIR / "ultimate_selection" / "{{ run_id }}_ultimate_selection_review.xlsx"),
            ],
        },
    )

    generate_ultimate_selection_template = PythonOperator(
        task_id="generate_ultimate_selection_template",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "generate_ultimate_selection_template.py",
            "script_args": [
                "--segmentation-version",
                DEFAULT_SEGMENTATION_VERSION,
                "--output",
                str(DATA_PIPELINE_DIR / "ultimate_selection.xlsx"),
            ],
        },
    )

    open_ultimate_selection_review = PythonOperator(
        task_id="open_ultimate_selection_review",
        python_callable=create_review_request,
        op_kwargs={
            "checkpoint_name": "ultimate_selection",
            "workbook_name": "ultimate_selection.xlsx",
            "instructions": (
                "Review the exported ultimate selection workbook at "
                + str(REVIEW_PACKET_DIR / "ultimate_selection" / "{{ run_id }}_ultimate_selection_review.xlsx")
                + ", then update ultimate_selection.xlsx so each accident year picks one method "
                "for loss and one method for claim count, and save the workbook."
            ),
        },
    )

    wait_for_ultimate_selection_upload = PythonSensor(
        task_id="wait_for_ultimate_selection_upload",
        retries=0,
        **sensor_kwargs("ultimate_selection.xlsx", "open_ultimate_selection_review"),
    )

    upload_ultimate_selection = PythonOperator(
        task_id="upload_ultimate_selection",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "upload_actuarial_inputs.py",
            "script_args": build_upload_script_args("ultimate_selection.xlsx", "ultimate_selection"),
        },
    )

    # -------------------------------------------------
    # Selected Ultimate loss & ultimate claim counts
    # -------------------------------------------------

    dbt_build_selected_ultimate_metrics = PythonOperator(
        task_id="dbt_build_selected_ultimate_metrics",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": SELECTED_ULTIMATE_METRICS_MODELS},
        execution_timeout=timedelta(minutes=15),
    )

    export_frequency_severity_for_review = PythonOperator(
        task_id="export_frequency_severity_for_review",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "export_frequency_severity_review.py",
            "script_args": [
                "--output",
                str(REVIEW_PACKET_DIR / "trend_selection" / "{{ run_id }}_frequency_severity_review.xlsx"),
            ],
        },
    )

    open_trend_review = PythonOperator(
        task_id="open_trend_review",
        python_callable=create_review_request,
        op_kwargs={
            "checkpoint_name": "trend_selection",
            "workbook_name": "trend_selection.xlsx",
            "instructions": (
                "Review the exported frequency/severity workbook at "
                + str(REVIEW_PACKET_DIR / "trend_selection" / "{{ run_id }}_frequency_severity_review.xlsx")
                + ", then update the frequency and severity trend assumptions, and save the workbook."
            ),
        },
    )

    wait_for_trend_selection_upload = PythonSensor(
        task_id="wait_for_trend_selection_upload",
        retries=0,
        **sensor_kwargs("trend_selection.xlsx", "open_trend_review"),
    )

    upload_trend_selection = PythonOperator(
        task_id="upload_trend_selection",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "upload_actuarial_inputs.py",
            "script_args": build_upload_script_args("trend_selection.xlsx", "trend_selection"),
        },
    )

    # -------------------
    # Pure Premium
    # -------------------

    dbt_build_trended_metrics = PythonOperator(
        task_id="dbt_build_trended_metrics",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": TRENDED_METRICS_MODELS},
        execution_timeout=timedelta(minutes=15),
    )

    open_expense_review = PythonOperator(
        task_id="open_expense_review",
        python_callable=create_review_request,
        op_kwargs={
            "checkpoint_name": "expense_assumption",
            "workbook_name": "expense_assumption.xlsx",
            "instructions": (
                "Update expense and profit assumptions for each state, then save the workbook."
            ),
        },
    )

    wait_for_expense_assumption_upload = PythonSensor(
        task_id="wait_for_expense_assumption_upload",
        retries=0,
        **sensor_kwargs("expense_assumption.xlsx", "open_expense_review"),
    )

    upload_expense_assumption = PythonOperator(
        task_id="upload_expense_assumption",
        python_callable=run_python_script,
        op_kwargs={
            "script_name": "upload_actuarial_inputs.py",
            "script_args": build_upload_script_args("expense_assumption.xlsx", "expense_assumption"),
        },
    )

    # -------------------
    # Indicated Premium
    # -------------------

    dbt_build_indication = PythonOperator(
        task_id="dbt_build_indication",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": INDICATION_MODELS},
        execution_timeout=timedelta(minutes=15),
    )

    dbt_build_controls_summary = PythonOperator(
        task_id="dbt_build_controls_summary",
        python_callable=run_dbt_build,
        op_kwargs={"model_names": CONTROL_SUMMARY_MODELS},
        execution_timeout=timedelta(minutes=15),
    )

    (
        generate_simulated_data
        >> dbt_build_triangle_models
        >> export_triangle_for_ldf_review
        >> open_ldf_review
        >> wait_for_ldf_selection_upload
        >> upload_ldf_selection
        >> dbt_build_chain_ladder
        >> export_ultimate_for_review
        >> open_selected_ultimate_review
        >> wait_for_selected_ultimate_upload
        >> upload_selected_ultimate
        >> dbt_build_ultimate_candidates
        >> export_ultimate_selection_for_review
        >> generate_ultimate_selection_template
        >> open_ultimate_selection_review
        >> wait_for_ultimate_selection_upload
        >> upload_ultimate_selection
        >> dbt_build_selected_ultimate_metrics
        >> export_frequency_severity_for_review
        >> open_trend_review
        >> wait_for_trend_selection_upload
        >> upload_trend_selection
        >> dbt_build_trended_metrics
        >> open_expense_review
        >> wait_for_expense_assumption_upload
        >> upload_expense_assumption
        >> dbt_build_indication
        >> dbt_build_controls_summary
    )
