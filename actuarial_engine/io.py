"""Snowflake adapter for actuarial engine input and output contracts."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import pandas as pd

from platform_common.snowflake import (
    SnowflakeSettings,
    connect_snowflake,
    validate_identifier,
)

from .result_formatter import to_snowflake_columns

if TYPE_CHECKING:
    from .calculation import EngineRunResult


class SnowflakeRepository:
    TRIANGLE_RELATION = "INT_LOSS_TRIANGLE_POOLED"
    EXPECTED_INPUT_RELATION = "INT_DEVELOPMENT_EXPOSURE"
    OUTPUT_TABLES = {
        "ldf_observations": "ACTUARIAL_LDF_OBSERVATION",
        "ldf_candidates": "ACTUARIAL_LDF_CANDIDATE",
        "tail_candidates": "ACTUARIAL_TAIL_CANDIDATE",
        "model_candidates": "ACTUARIAL_MODEL_CANDIDATE",
        "diagnostics": "ACTUARIAL_MODEL_DIAGNOSTIC",
    }

    def __init__(self, settings: SnowflakeSettings):
        self.settings = settings
        for identifier in (
            settings.database,
            settings.schema,
            self.TRIANGLE_RELATION,
            self.EXPECTED_INPUT_RELATION,
            *self.OUTPUT_TABLES.values(),
        ):
            validate_identifier(identifier)

    @classmethod
    def from_environment(cls) -> "SnowflakeRepository":
        return cls(SnowflakeSettings.from_environment())

    def connect(self) -> Any:
        return connect_snowflake(self.settings, autocommit=False)

    def read_triangle(
        self, *, as_of_date: date, triangle_grains: tuple[str, ...]
    ) -> pd.DataFrame:
        """
            Read actual cumulative loss or expense
            models/intermediate/actuarial/developement/int_loss_triangle_pooled
            * represents you need to use keyword arguments to pass in the function
            correct: repository.read_triangle(as_of_date=date(2026, 6, 30), triangle_grains=("annual", "quarterly")
            incorrect: repository.read_triangle(date(2026, 6, 30), ("annual", "quarterly")
        """

        # placeholders == "%s, %s, %s"
        placeholders = ", ".join(["%s"] * len(triangle_grains))
        query = f"""
            SELECT *
            FROM {self._relation(self.TRIANGLE_RELATION)}
            WHERE VALUATION_DATE <= %s
              AND TRIANGLE_GRAIN IN ({placeholders})
        """

        # * is sequence unpacking
        # * for list/tuple; ** for dictionary
        # if triangle_grains = ("annual", "quarterly", "monthly")
        # (date(2026, 6, 30), "annual", "quarterly", "monthly",)
        return self._read(query, (as_of_date, *triangle_grains))

    def read_expected_input(
        self, *, as_of_date: date, triangle_grains: tuple[str, ...]
    ) -> pd.DataFrame:
        """Read exposures
           models/intermediate/actuarial/inputs/int_development_exposure
        """

        placeholders = ", ".join(["%s"] * len(triangle_grains))
        query = f"""
            SELECT *
            FROM {self._relation(self.EXPECTED_INPUT_RELATION)}
            WHERE ACCIDENT_PERIOD <= %s
              AND TRIANGLE_GRAIN IN ({placeholders})
        """
        return self._read(query, (as_of_date, *triangle_grains))

    def _read(self, query: str, parameters: tuple[object, ...]) -> pd.DataFrame:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(query, parameters)
                return cursor.fetch_pandas_all()
            finally:
                cursor.close()
        finally:
            connection.close()

    def write_run(self, result: "EngineRunResult") -> None:
        try:
            from snowflake.connector.pandas_tools import write_pandas
        except ImportError as error:
            raise RuntimeError(
                "Install the 'snowflake' optional dependency to use warehouse I/O"
            ) from error

        connection = self.connect()
        try:
            cursor = connection.cursor()
            try:
                for attribute, table in self.OUTPUT_TABLES.items():

                    # prevent duplicate results with the same model_run_id
                    cursor.execute(
                        f"DELETE FROM {self._relation(table)} WHERE MODEL_RUN_ID = %s",
                        (result.model_run_id,),
                    )

                    # getattr(result, attribute) = result.ldf_observations
                    #                            = result.ldf_candidates
                    #                            ...
                    frame = to_snowflake_columns(getattr(result, attribute))

                    # success, number_of_chunks, number_of_rows, copy_results
                    # write Pandas DataFrame into Snowflake table
                    # auto_create_table=False, so output tables should exist
                    success, _, row_count, _ = write_pandas(
                        connection,
                        frame,
                        table_name=table,
                        database=self.settings.database,
                        schema=self.settings.schema,
                        quote_identifiers=False,
                        use_logical_type=True,
                    )

                    # if ProgrammingError: table does not exist
                    # rollback transaction
                    # another ProgrammingError
                    # finally connection close
                    if not success or row_count != len(frame):
                        raise RuntimeError(
                            f"Incomplete write to {table}: {row_count}/{len(frame)} rows"
                        )
                connection.commit()
            finally:
                cursor.close()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _relation(self, table: str) -> str:
        return f"{self.settings.database}.{self.settings.schema}.{table}"
