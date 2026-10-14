"""Airflow REST adapter used after an approval is committed."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class AirflowTriggerResult:
    dag_run_id: str
    status: str
    response: dict[str, Any]


class AirflowClient(Protocol):
    dag_id: str

    def trigger(
        self,
        *,
        dag_run_id: str,
        conf: dict[str, Any],
    ) -> AirflowTriggerResult: ...


class AirflowRestClient:
    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        dag_id: str,
        timeout_seconds: int = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.dag_id = dag_id
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "AirflowClient":
        enabled = os.getenv("AIRFLOW_TRIGGER_ENABLED", "false").lower() == "true"
        if not enabled:
            return DisabledAirflowClient()
        return cls(
            base_url=os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080"),
            username=os.getenv("AIRFLOW_USERNAME", "admin"),
            password=os.getenv("AIRFLOW_PASSWORD", "admin"),
            dag_id=os.getenv(
                "AIRFLOW_DOWNSTREAM_DAG_ID", "approved_actuarial_pricing"
            ),
            timeout_seconds=int(os.getenv("AIRFLOW_REQUEST_TIMEOUT_SECONDS", "15")),
        )

    def trigger(
        self,
        *,
        dag_run_id: str,
        conf: dict[str, Any],
    ) -> AirflowTriggerResult:
        url = (
            f"{self.base_url}/api/v1/dags/{quote(self.dag_id, safe='')}"
            "/dagRuns"
        )
        payload = json.dumps({"dag_run_id": dag_run_id, "conf": conf}).encode()
        credentials = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode()
        request = Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode() or "{}")
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"Airflow trigger failed: {error}") from error
        return AirflowTriggerResult(
            dag_run_id=str(body.get("dag_run_id", dag_run_id)),
            status=str(body.get("state", "QUEUED")).upper(),
            response=body,
        )


class DisabledAirflowClient:
    dag_id = "approved_actuarial_pricing"

    def trigger(
        self,
        *,
        dag_run_id: str,
        conf: dict[str, Any],
    ) -> AirflowTriggerResult:
        return AirflowTriggerResult(
            dag_run_id=dag_run_id,
            status="DISABLED",
            response={"conf": conf, "message": "Airflow triggering is disabled"},
        )
