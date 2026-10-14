"""Snowflake persistence adapter for the workflow service layer."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from platform_common.snowflake import (
    SnowflakeSettings,
    connect_snowflake,
    validate_identifier,
)

from .domain import CandidateType, SelectionStatus, SelectionVersion
from .errors import InvalidTransitionError, WorkflowNotFoundError


class SnowflakeWorkflowRepository:
    CANDIDATE_TABLES = {
        CandidateType.LDF: "ACTUARIAL_LDF_CANDIDATE",
        CandidateType.TAIL: "ACTUARIAL_TAIL_CANDIDATE",
        CandidateType.ULTIMATE: "ACTUARIAL_MODEL_CANDIDATE",
    }
    SELECTION_TABLES = {
        CandidateType.LDF: "ACTUARIAL_LDF_SELECTION",
        CandidateType.TAIL: "ACTUARIAL_TAIL_SELECTION",
        CandidateType.ULTIMATE: "ACTUARIAL_ULTIMATE_SELECTION",
    }
    SELECTION_COLUMNS = {
        CandidateType.LDF: (
            "TRIANGLE_GRAIN",
            "DEVELOPMENT_POOL_ID",
            "POOL_LEVEL",
            "LINE_OF_BUSINESS",
            "MEASURE_TYPE",
            "FROM_AGE_MONTHS",
            "TO_AGE_MONTHS",
            "SELECTED_METHOD",
            "SELECTED_LDF",
            "SELECTION_SOURCE",
            "SELECTION_REASON",
        ),
        CandidateType.TAIL: (
            "TRIANGLE_GRAIN",
            "DEVELOPMENT_POOL_ID",
            "POOL_LEVEL",
            "LINE_OF_BUSINESS",
            "MEASURE_TYPE",
            "DEVELOPMENT_METHOD",
            "SELECTED_TAIL_METHOD",
            "SELECTED_TAIL_FACTOR",
            "SELECTION_SOURCE",
            "SELECTION_REASON",
        ),
        CandidateType.ULTIMATE: (
            "TRIANGLE_GRAIN",
            "DEVELOPMENT_POOL_ID",
            "POOL_LEVEL",
            "LINE_OF_BUSINESS",
            "MEASURE_TYPE",
            "ACCIDENT_PERIOD",
            "DEVELOPMENT_METHOD",
            "TAIL_METHOD",
            "SELECTED_ULTIMATE_METHOD",
            "SELECTED_ULTIMATE_VALUE",
            "SELECTION_SOURCE",
            "SELECTION_REASON",
        ),
    }
    VERSION_TABLE = "ACTUARIAL_SELECTION_VERSION"
    AUDIT_TABLE = "ACTUARIAL_APPROVAL_EVENT"
    PIPELINE_TABLE = "ACTUARIAL_PIPELINE_RUN"
    FILTER_COLUMNS = {
        "triangle_grain": "TRIANGLE_GRAIN",
        "development_pool_id": "DEVELOPMENT_POOL_ID",
        "line_of_business": "LINE_OF_BUSINESS",
        "measure_type": "MEASURE_TYPE",
    }

    def __init__(self, settings: SnowflakeSettings) -> None:
        self.settings = settings
        for identifier in (
            settings.database,
            settings.schema,
            self.VERSION_TABLE,
            self.AUDIT_TABLE,
            self.PIPELINE_TABLE,
            *self.CANDIDATE_TABLES.values(),
            *self.SELECTION_TABLES.values(),
        ):
            validate_identifier(identifier)

    @classmethod
    def from_environment(cls) -> "SnowflakeWorkflowRepository":
        return cls(SnowflakeSettings.from_environment())

    def list_model_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        limit = _safe_limit(limit, maximum=10_000)
        table = self._relation(self.CANDIDATE_TABLES[CandidateType.ULTIMATE])
        query = f"""
            SELECT
                MODEL_RUN_ID,
                AS_OF_DATE,
                ENGINE_NAME,
                ENGINE_VERSION,
                CALCULATION_LIBRARY,
                CALCULATION_LIBRARY_VERSION,
                MIN(CREATED_AT) AS CREATED_AT,
                COUNT(*) AS CANDIDATE_COUNT
            FROM {table}
            GROUP BY
                MODEL_RUN_ID,
                AS_OF_DATE,
                ENGINE_NAME,
                ENGINE_VERSION,
                CALCULATION_LIBRARY,
                CALCULATION_LIBRARY_VERSION
            ORDER BY CREATED_AT DESC
            LIMIT {limit}
        """
        return self._read(query)

    def list_candidates(
        self,
        candidate_type: CandidateType,
        model_run_id: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = 10_000,
    ) -> list[dict[str, Any]]:
        limit = _safe_limit(limit, maximum=100_000)
        clauses = ["MODEL_RUN_ID = %s"]
        parameters: list[Any] = [model_run_id]
        for key, value in (filters or {}).items():
            if value is None or value == "":
                continue
            column = self.FILTER_COLUMNS.get(key)
            if column is None:
                raise ValueError(f"Unsupported candidate filter: {key}")
            clauses.append(f"{column} = %s")
            parameters.append(value)
        table = self._relation(self.CANDIDATE_TABLES[candidate_type])
        query = f"""
            SELECT *
            FROM {table}
            WHERE {' AND '.join(clauses)}
            ORDER BY TRIANGLE_GRAIN, DEVELOPMENT_POOL_ID, MEASURE_TYPE
            LIMIT {limit}
        """
        return self._read(query, tuple(parameters))

    def create_version(
        self,
        version: SelectionVersion,
        *,
        actor: str,
    ) -> SelectionVersion:
        with self._transaction() as (_, cursor):
            cursor.execute(
                f"""
                INSERT INTO {self._relation(self.VERSION_TABLE)} (
                    SELECTION_VERSION_ID, MODEL_RUN_ID, AS_OF_DATE, STATUS,
                    CREATED_BY, CREATED_AT, COMMENT, ROW_VERSION
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    version.selection_version_id,
                    version.model_run_id,
                    version.as_of_date,
                    version.status.value,
                    version.created_by,
                    version.created_at,
                    version.comment,
                    version.row_version,
                ),
            )
            self._insert_event(
                cursor,
                version.selection_version_id,
                event_type="CREATED",
                from_status=None,
                to_status=version.status,
                actor=actor,
                comment=version.comment,
                details={"model_run_id": version.model_run_id},
            )
        return version

    def get_version(self, selection_version_id: str) -> SelectionVersion | None:
        rows = self._read(
            f"SELECT * FROM {self._relation(self.VERSION_TABLE)} "
            "WHERE SELECTION_VERSION_ID = %s",
            (selection_version_id,),
        )
        return _version_from_row(rows[0]) if rows else None

    def list_versions(
        self,
        *,
        status: SelectionStatus | None = None,
        limit: int = 100,
    ) -> list[SelectionVersion]:
        limit = _safe_limit(limit, maximum=10_000)
        query = f"SELECT * FROM {self._relation(self.VERSION_TABLE)}"
        parameters: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE STATUS = %s"
            parameters = (status.value,)
        query += f" ORDER BY CREATED_AT DESC LIMIT {limit}"
        return [_version_from_row(row) for row in self._read(query, parameters)]

    def replace_selections(
        self,
        candidate_type: CandidateType,
        selection_version_id: str,
        records: list[dict[str, Any]],
        *,
        actor: str,
    ) -> None:
        table = self._relation(self.SELECTION_TABLES[candidate_type])
        columns = self.SELECTION_COLUMNS[candidate_type]
        now = datetime.now(timezone.utc)
        insert_columns = (
            "SELECTION_VERSION_ID",
            *columns,
            "CREATED_BY",
            "CREATED_AT",
        )
        placeholders = ", ".join(["%s"] * len(insert_columns))
        with self._transaction() as (_, cursor):
            version = self._get_version_with_cursor(cursor, selection_version_id)
            if version is None:
                raise WorkflowNotFoundError(
                    f"Selection version {selection_version_id!r} was not found"
                )
            if version.status != SelectionStatus.DRAFT:
                raise InvalidTransitionError("Only DRAFT versions can be edited")
            cursor.execute(
                f"DELETE FROM {table} WHERE SELECTION_VERSION_ID = %s",
                (selection_version_id,),
            )
            values = []
            for record in records:
                normalized = {key.upper(): value for key, value in record.items()}
                values.append(
                    (
                        selection_version_id,
                        *(normalized[column] for column in columns),
                        actor,
                        now,
                    )
                )
            cursor.executemany(
                f"INSERT INTO {table} ({', '.join(insert_columns)}) "
                f"VALUES ({placeholders})",
                values,
            )
            self._insert_event(
                cursor,
                selection_version_id,
                event_type=f"{candidate_type.value.upper()}_SELECTIONS_REPLACED",
                from_status=SelectionStatus.DRAFT,
                to_status=SelectionStatus.DRAFT,
                actor=actor,
                comment=None,
                details={"row_count": len(records)},
            )

    def get_selections(
        self,
        selection_version_id: str,
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            kind.value: self._read(
                f"SELECT * FROM {self._relation(table)} "
                "WHERE SELECTION_VERSION_ID = %s",
                (selection_version_id,),
            )
            for kind, table in self.SELECTION_TABLES.items()
        }

    def transition_version(
        self,
        selection_version_id: str,
        *,
        expected_status: SelectionStatus,
        target_status: SelectionStatus,
        actor: str,
        comment: str | None,
    ) -> SelectionVersion:
        actor_column, time_column = {
            SelectionStatus.SUBMITTED: ("SUBMITTED_BY", "SUBMITTED_AT"),
            SelectionStatus.APPROVED: ("APPROVED_BY", "APPROVED_AT"),
            SelectionStatus.REJECTED: ("REJECTED_BY", "REJECTED_AT"),
        }[target_status]
        now = datetime.now(timezone.utc)
        with self._transaction() as (_, cursor):
            cursor.execute(
                f"""
                UPDATE {self._relation(self.VERSION_TABLE)}
                SET STATUS = %s,
                    {actor_column} = %s,
                    {time_column} = %s,
                    REVIEW_COMMENT = %s,
                    ROW_VERSION = ROW_VERSION + 1
                WHERE SELECTION_VERSION_ID = %s
                  AND STATUS = %s
                """,
                (
                    target_status.value,
                    actor,
                    now,
                    comment,
                    selection_version_id,
                    expected_status.value,
                ),
            )
            if cursor.rowcount != 1:
                raise InvalidTransitionError(
                    f"Expected {expected_status.value} selection version for transition"
                )
            self._insert_event(
                cursor,
                selection_version_id,
                event_type=target_status.value,
                from_status=expected_status,
                to_status=target_status,
                actor=actor,
                comment=comment,
                details=None,
            )
            version = self._get_version_with_cursor(cursor, selection_version_id)
        assert version is not None
        return version

    def record_pipeline_run(self, record: dict[str, Any]) -> None:
        columns = (
            "PIPELINE_RUN_ID",
            "SELECTION_VERSION_ID",
            "MODEL_RUN_ID",
            "AIRFLOW_DAG_ID",
            "AIRFLOW_DAG_RUN_ID",
            "STATUS",
            "TRIGGERED_BY",
            "TRIGGERED_AT",
            "ERROR_MESSAGE",
        )
        values = tuple(record[column.lower()] for column in columns)
        with self._transaction() as (_, cursor):
            cursor.execute(
                f"INSERT INTO {self._relation(self.PIPELINE_TABLE)} "
                f"({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})",
                values,
            )

    def update_pipeline_run(
        self,
        pipeline_run_id: str,
        *,
        status: str,
        error_message: str | None = None,
    ) -> None:
        with self._transaction() as (_, cursor):
            cursor.execute(
                f"""
                UPDATE {self._relation(self.PIPELINE_TABLE)}
                SET STATUS = %s,
                    ERROR_MESSAGE = %s,
                    UPDATED_AT = %s
                WHERE PIPELINE_RUN_ID = %s
                  AND STATUS = 'TRIGGERING'
                """,
                (status, error_message, datetime.now(timezone.utc), pipeline_run_id),
            )

    def initialize_schema(self) -> None:
        sql_path = Path(__file__).resolve().parent / "sql" / "create_workflow_tables.sql"
        connection = connect_snowflake(self.settings, autocommit=False)
        try:
            connection.execute_string(sql_path.read_text(encoding="utf-8"))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _read(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        connection = connect_snowflake(self.settings, autocommit=False)
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(query, parameters)
                columns = [str(item[0]).lower() for item in cursor.description]
                return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            finally:
                cursor.close()
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[tuple[Any, Any]]:
        connection = connect_snowflake(self.settings, autocommit=False)
        cursor = connection.cursor()
        try:
            yield connection, cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def _get_version_with_cursor(
        self,
        cursor: Any,
        selection_version_id: str,
    ) -> SelectionVersion | None:
        cursor.execute(
            f"SELECT * FROM {self._relation(self.VERSION_TABLE)} "
            "WHERE SELECTION_VERSION_ID = %s",
            (selection_version_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [str(item[0]).lower() for item in cursor.description]
        return _version_from_row(dict(zip(columns, row, strict=True)))

    def _insert_event(
        self,
        cursor: Any,
        selection_version_id: str,
        *,
        event_type: str,
        from_status: SelectionStatus | None,
        to_status: SelectionStatus,
        actor: str,
        comment: str | None,
        details: dict[str, Any] | None,
    ) -> None:
        import json

        cursor.execute(
            f"""
            INSERT INTO {self._relation(self.AUDIT_TABLE)} (
                EVENT_ID, SELECTION_VERSION_ID, EVENT_TYPE,
                FROM_STATUS, TO_STATUS, ACTOR, COMMENT, DETAILS, CREATED_AT
            )
            SELECT %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s
            """,
            (
                str(uuid4()),
                selection_version_id,
                event_type,
                from_status.value if from_status else None,
                to_status.value,
                actor,
                comment,
                json.dumps(details or {}),
                datetime.now(timezone.utc),
            ),
        )

    def _relation(self, table: str) -> str:
        return f"{self.settings.database}.{self.settings.schema}.{table}"


def _version_from_row(row: dict[str, Any]) -> SelectionVersion:
    return SelectionVersion(
        selection_version_id=str(row["selection_version_id"]),
        model_run_id=str(row["model_run_id"]),
        as_of_date=_date_value(row["as_of_date"]),
        status=SelectionStatus(str(row["status"])),
        created_by=str(row["created_by"]),
        created_at=row["created_at"],
        comment=row.get("comment"),
        submitted_by=row.get("submitted_by"),
        submitted_at=row.get("submitted_at"),
        approved_by=row.get("approved_by"),
        approved_at=row.get("approved_at"),
        rejected_by=row.get("rejected_by"),
        rejected_at=row.get("rejected_at"),
        review_comment=row.get("review_comment"),
        row_version=int(row["row_version"]),
    )


def _date_value(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _safe_limit(value: int, *, maximum: int) -> int:
    if value < 1 or value > maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return int(value)
