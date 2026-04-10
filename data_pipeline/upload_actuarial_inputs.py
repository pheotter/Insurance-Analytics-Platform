import argparse
import getpass
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

ASSUMPTION_VERSION_TABLE = "ASSUMPTION_VERSION"
ASSUMPTION_CHANGE_LOG_TABLE = "ASSUMPTION_CHANGE_LOG"
PIPELINE_RUN_METADATA_TABLE = "PIPELINE_RUN_METADATA"
DIFF_REPORT_DIR = Path(__file__).resolve().parent / "governance_reports"

FILES = {
    "ldf_selection_table.xlsx": {
        "table_name": "LDF_SELECTION_TABLE",
        "assumption_type": "ldf_selection",
        "key_columns": [
            "SEGMENTATION_VERSION",
            "TRIANGLE_TYPE",
            "STATE",
            "RISK_CLASS",
            "VEHICLE_SEGMENT",
            "DEVELOPMENT",
        ],
    },
    "selected_ultimate.xlsx": {
        "table_name": "SELECTED_ULTIMATE",
        "assumption_type": "selected_ultimate",
        "key_columns": [
            "SEGMENTATION_VERSION",
            "TYPE",
            "STATE",
            "RISK_CLASS",
            "VEHICLE_SEGMENT",
            "ACCIDENT_YEAR",
            "METHOD",
        ],
    },
    "ultimate_selection.xlsx": {
        "table_name": "ULTIMATE_SELECTION",
        "assumption_type": "ultimate_selection",
        "key_columns": [
            "SEGMENTATION_VERSION",
            "TYPE",
            "STATE",
            "RISK_CLASS",
            "VEHICLE_SEGMENT",
            "ACCIDENT_YEAR",
        ],
    },
    "trend_selection.xlsx": {
        "table_name": "TREND_SELECTION",
        "assumption_type": "trend_selection",
        "key_columns": [
            "SEGMENTATION_VERSION",
            "TREND_TYPE",
            "STATE",
            "RISK_CLASS",
            "VEHICLE_SEGMENT",
        ],
    },
    "expense_assumption.xlsx": {
        "table_name": "EXPENSE_ASSUMPTION",
        "assumption_type": "expense_assumption",
        "key_columns": [
            "PRICING_VERSION",
            "STATE",
        ],
    },
}


def get_env(name, default=None):
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_connection():
    private_key_path = get_env("SNOWFLAKE_PRIVATE_KEY_PATH").replace("\r", "").strip()

    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend(),
        ).private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    return snowflake.connector.connect(
        user=get_env("SNOWFLAKE_USER"),
        account=get_env("SNOWFLAKE_ACCOUNT"),
        role=get_env("SNOWFLAKE_ROLE"),
        warehouse=get_env("SNOWFLAKE_WAREHOUSE"),
        database=get_env("SNOWFLAKE_DATABASE"),
        schema=get_env("SNOWFLAKE_SCHEMA"),
        private_key=private_key,
    )


def resolve_requested_files(requested_files):
    if not requested_files:
        return FILES

    resolved = {}
    for file_name in requested_files:
        normalized = Path(file_name).name
        if normalized not in FILES:
            valid_files = ", ".join(sorted(FILES))
            raise ValueError(f"Unsupported file '{file_name}'. Valid options: {valid_files}")
        resolved[normalized] = FILES[normalized]
    return resolved


def normalize_dataframe(df):
    normalized = df.copy()
    normalized.columns = normalized.columns.str.upper()
    return normalized


def normalize_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value).strip()


def prepare_dataframe_for_diff(df, key_columns):
    if df.empty:
        return pd.DataFrame(columns=["ROW_KEY", *key_columns]).set_index("ROW_KEY")

    prepared = normalize_dataframe(df)
    missing = [column for column in key_columns if column not in prepared.columns]
    if missing:
        raise ValueError(f"Missing key columns for diffing: {missing}")

    for column in prepared.columns:
        prepared[column] = prepared[column].map(normalize_value)

    prepared["ROW_KEY"] = prepared[key_columns].apply(
        lambda row: "|".join("" if value is None else str(value) for value in row),
        axis=1,
    )

    duplicate_keys = prepared["ROW_KEY"][prepared["ROW_KEY"].duplicated()].unique().tolist()
    if duplicate_keys:
        sample_keys = ", ".join(duplicate_keys[:5])
        raise ValueError(
            "Duplicate natural keys detected while preparing diff rows. "
            f"Please review key_columns={key_columns}. Sample duplicated keys: {sample_keys}"
        )

    return prepared.set_index("ROW_KEY", drop=True)


def load_current_table(conn, table_name):
    cursor = conn.cursor()
    try:
        cursor.execute(f"select * from {table_name}")
    except snowflake.connector.errors.ProgrammingError as exc:
        if "does not exist" in str(exc).lower():
            return pd.DataFrame()
        raise

    rows = cursor.fetchall()
    if cursor.description is None:
        return pd.DataFrame()
    columns = [item[0] for item in cursor.description]
    return pd.DataFrame(rows, columns=columns)


def ensure_diff_report_dir():
    DIFF_REPORT_DIR.mkdir(parents=True, exist_ok=True)



def ensure_governance_tables(conn):
    ddl_statements = [
        f"""
        create table if not exists {ASSUMPTION_VERSION_TABLE} (
            ASSUMPTION_SET_ID string,
            ASSUMPTION_TYPE string,
            FILE_NAME string,
            TARGET_TABLE_NAME string,
            VERSION_SEQUENCE number,
            VERSION_LABEL string,
            STATUS string,
            UPLOADED_AT timestamp_ntz,
            UPLOADED_BY string,
            UPLOAD_COMMENT string,
            SOURCE_ROW_COUNT number,
            CHANGE_COUNT number,
            PREVIOUS_ASSUMPTION_SET_ID string,
            DAG_ID string,
            DAG_RUN_ID string,
            TASK_ID string
        )
        """,
        f"""
        create table if not exists {ASSUMPTION_CHANGE_LOG_TABLE} (
            ASSUMPTION_SET_ID string,
            ASSUMPTION_TYPE string,
            FILE_NAME string,
            ROW_KEY string,
            CHANGE_TYPE string,
            COLUMN_NAME string,
            OLD_VALUE string,
            NEW_VALUE string,
            CHANGED_AT timestamp_ntz
        )
        """,
        f"""
        create table if not exists {PIPELINE_RUN_METADATA_TABLE} (
            PIPELINE_RUN_METADATA_ID string,
            DAG_ID string,
            DAG_RUN_ID string,
            TASK_ID string,
            ASSUMPTION_SET_ID string,
            ASSUMPTION_TYPE string,
            FILE_NAME string,
            VERSION_SEQUENCE number,
            VERSION_LABEL string,
            REGISTERED_AT timestamp_ntz
        )
        """,
    ]

    cursor = conn.cursor()
    try:
        for ddl in ddl_statements:
            cursor.execute(ddl)
    finally:
        cursor.close()


def get_next_version_info(conn, assumption_type):
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            select
                coalesce(max(VERSION_SEQUENCE), 0) as CURRENT_MAX
            from {ASSUMPTION_VERSION_TABLE}
            where ASSUMPTION_TYPE = %s
            """,
            (assumption_type,),
        )
        current_max = cursor.fetchone()[0]
        cursor.execute(
            f"""
            select ASSUMPTION_SET_ID
            from {ASSUMPTION_VERSION_TABLE}
            where ASSUMPTION_TYPE = %s
            order by VERSION_SEQUENCE desc
            limit 1
            """,
            (assumption_type,),
        )
        previous_row = cursor.fetchone()
        previous_assumption_set_id = previous_row[0] if previous_row else None
    finally:
        cursor.close()

    next_sequence = int(current_max or 0) + 1
    return next_sequence, previous_assumption_set_id


def build_change_log(previous_df, current_df, key_columns, assumption_set_id, assumption_type, file_name):
    previous_prepared = prepare_dataframe_for_diff(previous_df, key_columns)
    current_prepared = prepare_dataframe_for_diff(current_df, key_columns)

    previous_keys = set(previous_prepared.index)
    current_keys = set(current_prepared.index)
    all_keys = sorted(previous_keys | current_keys)

    changes = []
    changed_at = datetime.now(timezone.utc)

    for row_key in all_keys:
        if row_key not in previous_keys:
            row_payload = current_prepared.loc[row_key].to_dict()
            changes.append(
                {
                    "ASSUMPTION_SET_ID": assumption_set_id,
                    "ASSUMPTION_TYPE": assumption_type,
                    "FILE_NAME": file_name,
                    "ROW_KEY": row_key,
                    "CHANGE_TYPE": "added",
                    "COLUMN_NAME": "__row__",
                    "OLD_VALUE": None,
                    "NEW_VALUE": json.dumps(row_payload, ensure_ascii=True, sort_keys=True),
                    "CHANGED_AT": changed_at,
                }
            )
            continue

        if row_key not in current_keys:
            row_payload = previous_prepared.loc[row_key].to_dict()
            changes.append(
                {
                    "ASSUMPTION_SET_ID": assumption_set_id,
                    "ASSUMPTION_TYPE": assumption_type,
                    "FILE_NAME": file_name,
                    "ROW_KEY": row_key,
                    "CHANGE_TYPE": "removed",
                    "COLUMN_NAME": "__row__",
                    "OLD_VALUE": json.dumps(row_payload, ensure_ascii=True, sort_keys=True),
                    "NEW_VALUE": None,
                    "CHANGED_AT": changed_at,
                }
            )
            continue

        previous_row = previous_prepared.loc[row_key]
        current_row = current_prepared.loc[row_key]
        for column in current_prepared.columns:
            old_value = previous_row.get(column)
            new_value = current_row.get(column)
            if old_value != new_value:
                changes.append(
                    {
                        "ASSUMPTION_SET_ID": assumption_set_id,
                        "ASSUMPTION_TYPE": assumption_type,
                        "FILE_NAME": file_name,
                        "ROW_KEY": row_key,
                        "CHANGE_TYPE": "updated",
                        "COLUMN_NAME": column,
                        "OLD_VALUE": old_value,
                        "NEW_VALUE": new_value,
                        "CHANGED_AT": changed_at,
                    }
                )

    return changes


def write_diff_report(file_name, assumption_type, version_label, author, comment, changes):
    ensure_diff_report_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report_path = DIFF_REPORT_DIR / f"{timestamp}_{Path(file_name).stem}_diff.md"

    added_count = sum(change["CHANGE_TYPE"] == "added" for change in changes)
    removed_count = sum(change["CHANGE_TYPE"] == "removed" for change in changes)
    updated_count = sum(change["CHANGE_TYPE"] == "updated" for change in changes)

    lines = [
        f"# Diff Report: {file_name}",
        "",
        f"- Assumption type: {assumption_type}",
        f"- Version label: {version_label}",
        f"- Author: {author}",
        f"- Comment: {comment or '(none)'}",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        f"- Total changes: {len(changes)}",
        f"- Added rows: {added_count}",
        f"- Removed rows: {removed_count}",
        f"- Updated fields: {updated_count}",
        "",
    ]

    if not changes:
        lines.extend(["No differences detected.", ""])
    else:
        lines.extend(
            [
                "## Changes",
                "",
                "| change_type | row_key | column_name | old_value | new_value |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for change in changes[:200]:
            old_value = str(change["OLD_VALUE"]).replace("\n", " ") if change["OLD_VALUE"] is not None else ""
            new_value = str(change["NEW_VALUE"]).replace("\n", " ") if change["NEW_VALUE"] is not None else ""
            lines.append(
                f"| {change['CHANGE_TYPE']} | {change['ROW_KEY']} | {change['COLUMN_NAME']} | {old_value} | {new_value} |"
            )
        if len(changes) > 200:
            lines.extend(["", f"... truncated {len(changes) - 200} additional change rows ..."])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def insert_assumption_version(
    conn,
    assumption_set_id,
    assumption_type,
    file_name,
    table_name,
    version_sequence,
    version_label,
    author,
    comment,
    row_count,
    change_count,
    previous_assumption_set_id,
    dag_id,
    dag_run_id,
    task_id,
):
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            insert into {ASSUMPTION_VERSION_TABLE} (
                ASSUMPTION_SET_ID,
                ASSUMPTION_TYPE,
                FILE_NAME,
                TARGET_TABLE_NAME,
                VERSION_SEQUENCE,
                VERSION_LABEL,
                STATUS,
                UPLOADED_AT,
                UPLOADED_BY,
                UPLOAD_COMMENT,
                SOURCE_ROW_COUNT,
                CHANGE_COUNT,
                PREVIOUS_ASSUMPTION_SET_ID,
                DAG_ID,
                DAG_RUN_ID,
                TASK_ID
            )
            values (%s, %s, %s, %s, %s, %s, %s, current_timestamp(), %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                assumption_set_id,
                assumption_type,
                file_name,
                table_name,
                version_sequence,
                version_label,
                "uploaded",
                author,
                comment,
                row_count,
                change_count,
                previous_assumption_set_id,
                dag_id,
                dag_run_id,
                task_id,
            ),
        )
    finally:
        cursor.close()


def insert_change_log(conn, changes):
    if not changes:
        return

    rows = [
        (
            change["ASSUMPTION_SET_ID"],
            change["ASSUMPTION_TYPE"],
            change["FILE_NAME"],
            change["ROW_KEY"],
            change["CHANGE_TYPE"],
            change["COLUMN_NAME"],
            change["OLD_VALUE"],
            change["NEW_VALUE"],
            change["CHANGED_AT"],
        )
        for change in changes
    ]

    cursor = conn.cursor()
    try:
        cursor.executemany(
            f"""
            insert into {ASSUMPTION_CHANGE_LOG_TABLE} (
                ASSUMPTION_SET_ID,
                ASSUMPTION_TYPE,
                FILE_NAME,
                ROW_KEY,
                CHANGE_TYPE,
                COLUMN_NAME,
                OLD_VALUE,
                NEW_VALUE,
                CHANGED_AT
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
    finally:
        cursor.close()


def insert_pipeline_run_metadata(
    conn,
    dag_id,
    dag_run_id,
    task_id,
    assumption_set_id,
    assumption_type,
    file_name,
    version_sequence,
    version_label,
):
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            insert into {PIPELINE_RUN_METADATA_TABLE} (
                PIPELINE_RUN_METADATA_ID,
                DAG_ID,
                DAG_RUN_ID,
                TASK_ID,
                ASSUMPTION_SET_ID,
                ASSUMPTION_TYPE,
                FILE_NAME,
                VERSION_SEQUENCE,
                VERSION_LABEL,
                REGISTERED_AT
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, current_timestamp())
            """,
            (
                str(uuid.uuid4()),
                dag_id,
                dag_run_id,
                task_id,
                assumption_set_id,
                assumption_type,
                file_name,
                version_sequence,
                version_label,
            ),
        )
    finally:
        cursor.close()


def upload_excel_to_snowflake(conn, file_path, file_config, author, comment, version_label, dag_id, dag_run_id, task_id):
    table_name = file_config["table_name"]
    assumption_type = file_config["assumption_type"]
    key_columns = file_config["key_columns"]

    new_df = normalize_dataframe(pd.read_excel(file_path))
    previous_df = load_current_table(conn, table_name)
    version_sequence, previous_assumption_set_id = get_next_version_info(conn, assumption_type)
    effective_version_label = version_label or f"auto_v{version_sequence}"
    assumption_set_id = str(uuid.uuid4())

    changes = build_change_log(
        previous_df=previous_df,
        current_df=new_df,
        key_columns=key_columns,
        assumption_set_id=assumption_set_id,
        assumption_type=assumption_type,
        file_name=file_path.name,
    )

    added_count = sum(change["CHANGE_TYPE"] == "added" for change in changes)
    removed_count = sum(change["CHANGE_TYPE"] == "removed" for change in changes)
    updated_count = sum(change["CHANGE_TYPE"] == "updated" for change in changes)
    print(
        f"{file_path.name}: preparing upload with {len(changes)} changes "
        f"({added_count} added, {removed_count} removed, {updated_count} updated fields/rows)."
    )
    diff_report_path = write_diff_report(
        file_name=file_path.name,
        assumption_type=assumption_type,
        version_label=effective_version_label,
        author=author,
        comment=comment,
        changes=changes,
    )
    print(f"{file_path.name}: diff report written to {diff_report_path}")

    success, _, nrows, _ = write_pandas(
        conn,
        new_df,
        table_name,
        auto_create_table=True,
        overwrite=True,
    )
    if not success:
        raise RuntimeError(f"Failed to upload workbook into {table_name}")

    insert_assumption_version(
        conn=conn,
        assumption_set_id=assumption_set_id,
        assumption_type=assumption_type,
        file_name=file_path.name,
        table_name=table_name,
        version_sequence=version_sequence,
        version_label=effective_version_label,
        author=author,
        comment=comment,
        row_count=nrows,
        change_count=len(changes),
        previous_assumption_set_id=previous_assumption_set_id,
        dag_id=dag_id,
        dag_run_id=dag_run_id,
        task_id=task_id,
    )
    insert_change_log(conn, changes)
    insert_pipeline_run_metadata(
        conn=conn,
        dag_id=dag_id,
        dag_run_id=dag_run_id,
        task_id=task_id,
        assumption_set_id=assumption_set_id,
        assumption_type=assumption_type,
        file_name=file_path.name,
        version_sequence=version_sequence,
        version_label=effective_version_label,
    )

    print(
        f"{table_name} uploaded from {file_path.name}: {nrows} rows "
        f"(version_sequence={version_sequence}, version_label={effective_version_label}, author={author})"
    )


def resolve_author(args):
    if args.author:
        return args.author
    if os.getenv("ASSUMPTION_AUTHOR"):
        return os.getenv("ASSUMPTION_AUTHOR")
    return getpass.getuser()


def resolve_comment(args):
    return args.comment or os.getenv("ASSUMPTION_COMMENT", "")


def resolve_pipeline_context(args):
    return (
        args.dag_id or os.getenv("AIRFLOW_CTX_DAG_ID"),
        args.dag_run_id or os.getenv("AIRFLOW_CTX_DAG_RUN_ID"),
        args.task_id or os.getenv("AIRFLOW_CTX_TASK_ID"),
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload actuarial workbook inputs to Snowflake."
    )
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        help="Workbook file name to upload. Repeat the flag to upload multiple files.",
    )
    parser.add_argument(
        "--author",
        help="Who is submitting this assumption update.",
    )
    parser.add_argument(
        "--comment",
        help="Short rationale or note for this upload.",
    )
    parser.add_argument(
        "--version",
        help="Optional version label to store alongside the upload metadata.",
    )
    parser.add_argument(
        "--dag-id",
        help="Optional Airflow DAG id override for pipeline metadata.",
    )
    parser.add_argument(
        "--dag-run-id",
        help="Optional Airflow DAG run id override for pipeline metadata.",
    )
    parser.add_argument(
        "--task-id",
        help="Optional Airflow task id override for pipeline metadata.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    selected_files = resolve_requested_files(args.files)
    project_dir = Path(__file__).resolve().parent
    author = resolve_author(args)
    comment = resolve_comment(args)
    dag_id, dag_run_id, task_id = resolve_pipeline_context(args)

    conn = build_connection()
    print("Connected to Snowflake securely using environment variables.")

    try:
        ensure_governance_tables(conn)
        for file_name, file_config in selected_files.items():
            upload_excel_to_snowflake(
                conn=conn,
                file_path=project_dir / file_name,
                file_config=file_config,
                author=author,
                comment=comment,
                version_label=args.version,
                dag_id=dag_id,
                dag_run_id=dag_run_id,
                task_id=task_id,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
