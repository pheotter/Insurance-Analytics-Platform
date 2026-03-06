import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
import csv
from snowflake.connector.pandas_tools import write_pandas
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

load_dotenv()

# ─────────────────────────────────────────
# Files and its corresponding tables
# ─────────────────────────────────────────

files = {
    "ldf_selection_table.xlsx": "LDF_SELECTION_TABLE",
    "selected_ultimate.xlsx": "SELECTED_ULTIMATE",
    "trend_selection.xlsx": "TREND_SELECTION",
    "expense_assumption.xlsx": "EXPENSE_ASSUMPTION"
}

# ─────────────────────────────────────────
# Read environment variables
# ─────────────────────────────────────────

SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
PRIVATE_KEY_PATH = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")

if not all([
    SNOWFLAKE_USER,
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_WAREHOUSE,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_SCHEMA,
    PRIVATE_KEY_PATH
]):
    raise ValueError("Missing one or more required Snowflake environment variables.")

# ─────────────────────────────────────────
# Load private key
# ─────────────────────────────────────────

with open(PRIVATE_KEY_PATH, "rb") as key:
    p_key = serialization.load_pem_private_key(
        key.read(),
        password=None,
        backend=default_backend()
    )

private_key = p_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# ─────────────────────────────────────────
# Connect
# ─────────────────────────────────────────

conn = snowflake.connector.connect(
    user=SNOWFLAKE_USER,
    account=SNOWFLAKE_ACCOUNT,
    warehouse=SNOWFLAKE_WAREHOUSE,
    database=SNOWFLAKE_DATABASE,
    schema=SNOWFLAKE_SCHEMA,
    private_key=private_key
)

print("Connected to Snowflake securely using environment variables.")

# ─────────────────────────────────────────────────────────
# upload function
# ─────────────────────────────────────────────────────────

def upload_excel_to_snowflake(file_path, table_name):

    df = pd.read_excel(file_path)

    # convert column names to uppercase
    df.columns = df.columns.str.upper()

    success, nchunks, nrows, _ = write_pandas(
        conn,
        df,
        table_name
    )

    print(f"{table_name} uploaded: {nrows} rows")

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

def main():

    for file, table in files.items():
        upload_excel_to_snowflake(file, table)

if __name__ == "__main__":
    main()
