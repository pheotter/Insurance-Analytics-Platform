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
        description="Generate the ultimate method selection workbook."
    )
    parser.add_argument("--segmentation-version", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def fetch_template_rows(conn, segmentation_version):
    query = """
        with candidates as (
            select state_grp, risk_class_grp, vehicle_segment_grp, accident_year, 'loss' as type
            from FCT_ULTIMATE_LOSS
            union
            select state_grp, risk_class_grp, vehicle_segment_grp, accident_year, 'claim_count' as type
            from FCT_ULTIMATE_CLAIM_COUNT
        )
        select
            %(segmentation_version)s as segmentation_version,
            type,
            state_grp as state,
            risk_class_grp as risk_class,
            vehicle_segment_grp as vehicle_segment,
            accident_year,
            cast(null as varchar) as method,
            cast(null as varchar) as comment
        from candidates
        order by state, risk_class, vehicle_segment, type, accident_year
    """
    cursor = conn.cursor()
    try:
        cursor.execute(query, {"segmentation_version": segmentation_version})
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
    finally:
        cursor.close()

    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        raise ValueError("No rows found to build ultimate selection template.")
    return df


def main():
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = build_connection()
    print("Connected to Snowflake securely using environment variables.")

    try:
        df = fetch_template_rows(conn, args.segmentation_version)
    finally:
        conn.close()

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        print(f"Generated ultimate selection template at {output_path}")
    except PermissionError:
        if output_path.exists() and output_path.stat().st_size > 0:
            print(
                "Could not overwrite the existing ultimate selection workbook. "
                f"Keeping the existing file in place: {output_path}"
            )
        else:
            raise


if __name__ == "__main__":
    main()
