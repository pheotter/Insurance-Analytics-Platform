import argparse
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()

FILES = {
    "ldf_selection_table.xlsx": "LDF_SELECTION_TABLE",
    "selected_ultimate.xlsx": "SELECTED_ULTIMATE",
    "ultimate_selection.xlsx": "ULTIMATE_SELECTION",
    "trend_selection.xlsx": "TREND_SELECTION",
    "expense_assumption.xlsx": "EXPENSE_ASSUMPTION",
}


def get_env(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_connection():
    private_key_path = get_env("SNOWFLAKE_PRIVATE_KEY_PATH")

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


def upload_excel_to_snowflake(conn, file_path, table_name):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.upper()

    success, _, nrows, _ = write_pandas(
        conn,
        df,
        table_name,
        auto_create_table=True,
        overwrite=True,
    )
    if not success:
        raise RuntimeError(f"Failed to upload workbook into {table_name}")
    print(f"{table_name} uploaded from {file_path.name}: {nrows} rows")


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
    return parser.parse_args()


def main():
    args = parse_args()
    selected_files = resolve_requested_files(args.files)
    project_dir = Path(__file__).resolve().parent

    conn = build_connection()
    print("Connected to Snowflake securely using environment variables.")

    try:
        for file_name, table_name in selected_files.items():
            upload_excel_to_snowflake(conn, project_dir / file_name, table_name)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
