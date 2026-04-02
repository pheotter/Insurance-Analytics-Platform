import argparse
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()


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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export frequency and severity review workbook by segment and accident year."
    )
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def fetch_review_data(conn):
    cursor = conn.cursor()
    try:
        count = cursor.execute("select count(*) from FCT_FREQUENCY_SEVERITY").fetchone()[0]
        print(f"FCT_FREQUENCY_SEVERITY row count: {count}")

        query = """
            select
                state_grp,
                risk_class_grp,
                vehicle_segment_grp,
                accident_year,
                frequency,
                severity
            from FCT_FREQUENCY_SEVERITY
            order by 1, 2, 3, 4
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    finally:
        cursor.close()

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        raise ValueError(
            "No rows found for frequency/severity review export. "
            "Check whether dbt_run_with_method_vars populated FCT_FREQUENCY_SEVERITY."
        )
    return df


def safe_sheet_name(index, segment_row):
    suffix = (
        f"{segment_row['STATE_GRP']}_{segment_row['RISK_CLASS_GRP']}_{segment_row['VEHICLE_SEGMENT_GRP']}"
        .replace("/", "_")
        .replace("\\", "_")
    )
    return f"fs_{index:03d}_{suffix}"[:31]


def export_workbook(df, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    segments = (
        df[["STATE_GRP", "RISK_CLASS_GRP", "VEHICLE_SEGMENT_GRP"]]
        .drop_duplicates()
        .sort_values(["STATE_GRP", "RISK_CLASS_GRP", "VEHICLE_SEGMENT_GRP"])
        .reset_index(drop=True)
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary = segments.copy()
        summary.insert(0, "sheet_name", "")

        for idx, segment_row in segments.iterrows():
            segment_key = (
                segment_row["STATE_GRP"],
                segment_row["RISK_CLASS_GRP"],
                segment_row["VEHICLE_SEGMENT_GRP"],
            )
            segment_df = df[
                (df["STATE_GRP"] == segment_key[0])
                & (df["RISK_CLASS_GRP"] == segment_key[1])
                & (df["VEHICLE_SEGMENT_GRP"] == segment_key[2])
            ].copy()
            sheet_name = safe_sheet_name(idx + 1, segment_row)
            summary.loc[idx, "sheet_name"] = sheet_name

            meta = pd.DataFrame(
                {
                    "field": ["state_grp", "risk_class_grp", "vehicle_segment_grp"],
                    "value": list(segment_key),
                }
            )
            meta.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)

            segment_df = segment_df.rename(
                columns={
                    "ACCIDENT_YEAR": "accident_year",
                    "FREQUENCY": "frequency",
                    "SEVERITY": "severity",
                }
            )
            segment_df[
                [
                    "accident_year",
                    "frequency",
                    "severity",
                ]
            ].to_excel(writer, sheet_name=sheet_name, index=False, startrow=5)

        summary.to_excel(writer, sheet_name="summary", index=False)

    print(f"Exported {len(segments)} segment frequency/severity sheets to {output_path}")


def main():
    args = parse_args()
    output_path = Path(args.output)

    conn = build_connection()
    print("Connected to Snowflake securely using environment variables.")

    try:
        df = fetch_review_data(conn)
    finally:
        conn.close()

    export_workbook(df, output_path)


if __name__ == "__main__":
    main()
