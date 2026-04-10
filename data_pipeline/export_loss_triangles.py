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
        description="Export cumulative paid and reported loss triangles to Excel."
    )
    parser.add_argument("--segmentation-version", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def fetch_triangle_data(conn, segmentation_version):
    df = pd.read_sql(
        "select * from int_claim_triangle_cumulative",
        conn,
    )
    if df.empty:
        raise ValueError(
            f"No rows found in int_claim_triangle_cumulative for segmentation version {segmentation_version}."
        )
    return df


def build_triangle(segment_df, value_column):
    triangle = (
        segment_df.pivot_table(
            index="ACCIDENT_YEAR",
            columns="DEVELOPMENT",
            values=value_column,
            aggfunc="sum",
        )
        .sort_index()
        .sort_index(axis=1)
    )
    triangle.columns = [f"dev_{int(col)}" for col in triangle.columns]
    return triangle.reset_index()


def safe_sheet_name(index, segment_row):
    suffix = (
        f"{segment_row['STATE_GRP']}_{segment_row['RISK_CLASS_GRP']}_{segment_row['VEHICLE_SEGMENT_GRP']}"
        .replace("/", "_")
        .replace("\\", "_")
    )
    return f"seg_{index:03d}_{suffix}"[:31]


def write_segment_sheet(writer, segment_key, segment_df, sheet_name):
    paid_triangle = build_triangle(segment_df, "CUMULATIVE_PAID")
    reported_triangle = build_triangle(segment_df, "CUMULATIVE_INCURRED")
    claim_count_triangle = build_triangle(segment_df, "CUMULATIVE_CLAIM_COUNT")

    segment_meta = pd.DataFrame(
        {
            "field": ["state_grp", "risk_class_grp", "vehicle_segment_grp"],
            "value": list(segment_key),
        }
    )
    segment_meta.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)

    pd.DataFrame({"cumulative_paid_triangle": []}).to_excel(
        writer, sheet_name=sheet_name, index=False, startrow=5
    )
    paid_triangle.to_excel(writer, sheet_name=sheet_name, index=False, startrow=6)

    reported_start = len(paid_triangle) + 10
    pd.DataFrame({"cumulative_reported_triangle": []}).to_excel(
        writer, sheet_name=sheet_name, index=False, startrow=reported_start
    )
    reported_triangle.to_excel(
        writer, sheet_name=sheet_name, index=False, startrow=reported_start + 1
    )

    claim_count_start = reported_start + len(reported_triangle) + 5
    pd.DataFrame({"cumulative_claim_count_triangle": []}).to_excel(
        writer, sheet_name=sheet_name, index=False, startrow=claim_count_start
    )
    claim_count_triangle.to_excel(
        writer, sheet_name=sheet_name, index=False, startrow=claim_count_start + 1
    )


def export_triangles(df, output_path, segmentation_version):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    segments = (
        df[["STATE_GRP", "RISK_CLASS_GRP", "VEHICLE_SEGMENT_GRP"]]
        .drop_duplicates()
        .sort_values(["STATE_GRP", "RISK_CLASS_GRP", "VEHICLE_SEGMENT_GRP"])
        .reset_index(drop=True)
    )

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary = segments.copy()
        summary.insert(0, "segmentation_version", segmentation_version)
        summary.insert(1, "sheet_name", "")

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
            ]
            sheet_name = safe_sheet_name(idx + 1, segment_row)
            summary.loc[idx, "sheet_name"] = sheet_name
            write_segment_sheet(writer, segment_key, segment_df, sheet_name)

        summary.to_excel(writer, sheet_name="summary", index=False)

    print(f"Exported {len(segments)} segment triangle sheets to {output_path}")


def main():
    args = parse_args()
    output_path = Path(args.output)

    conn = build_connection()
    print("Connected to Snowflake securely using environment variables.")

    try:
        df = fetch_triangle_data(conn, args.segmentation_version)
    finally:
        conn.close()

    export_triangles(df, output_path, args.segmentation_version)


if __name__ == "__main__":
    main()
