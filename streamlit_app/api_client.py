"""Small HTTP client used by the Streamlit presentation layer."""

from __future__ import annotations

from typing import Any

import requests


class ActuarialApiClient:
    def __init__(self, base_url: str, user: str, role: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Actuarial-User": user,
            "X-Actuarial-Role": role,
        }

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def model_runs(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/v1/model-runs")

    def candidates(self, model_run_id: str, candidate_type: str) -> list[dict]:
        return self._request(
            "GET",
            f"/api/v1/model-runs/{model_run_id}/candidates/{candidate_type}",
        )

    def create_version(self, model_run_id: str, comment: str | None) -> dict:
        return self._request(
            "POST",
            "/api/v1/selection-versions",
            json={"model_run_id": model_run_id, "comment": comment},
        )

    def versions(self, status: str | None = None) -> list[dict]:
        params = {"status": status} if status else None
        return self._request("GET", "/api/v1/selection-versions", params=params)

    def version(self, selection_version_id: str) -> dict:
        return self._request(
            "GET", f"/api/v1/selection-versions/{selection_version_id}"
        )

    def save_selections(
        self,
        selection_version_id: str,
        selection_type: str,
        selections: list[dict[str, Any]],
    ) -> dict:
        return self._request(
            "PUT",
            f"/api/v1/selection-versions/{selection_version_id}/"
            f"{selection_type}-selections",
            json={"selections": selections},
        )

    def action(
        self,
        selection_version_id: str,
        action: str,
        comment: str | None,
    ) -> dict:
        return self._request(
            "POST",
            f"/api/v1/selection-versions/{selection_version_id}/{action}",
            json={"comment": comment},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=30,
            **kwargs,
        )
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"API {response.status_code}: {detail}")
        return response.json()
