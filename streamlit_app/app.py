"""MVP actuarial candidate selection and approval interface."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import streamlit as st

from api_client import ActuarialApiClient


st.set_page_config(
    page_title="Actuarial Review Workbench",
    page_icon="AR",
    layout="wide",
)
st.title("Actuarial Review Workbench")
st.caption("Select, document, submit, and approve governed actuarial assumptions.")

with st.sidebar:
    st.header("Session")
    api_url = st.text_input(
        "API URL", value=os.getenv("ACTUARIAL_API_URL", "http://localhost:8000")
    )
    user = st.text_input("User", value=os.getenv("ACTUARIAL_USER", "actuary.demo"))
    role = st.selectbox(
        "Role",
        ["actuary", "reviewer", "admin", "viewer"],
        index=0,
    )
    page = st.radio("Workspace", ["Candidates", "Selections", "Approval queue"])

client = ActuarialApiClient(api_url, user, role)

try:
    client.health()
except Exception as error:
    st.error(f"API is unavailable: {error}")
    st.stop()


def select_version(versions: list[dict[str, Any]], key: str) -> dict[str, Any]:
    labels = {
        item["selection_version_id"]: (
            f"{item['selection_version_id'][:8]} | {item['status']} | "
            f"run {item['model_run_id'][:8]}"
        )
        for item in versions
    }
    selected_id = st.selectbox(
        "Selection version",
        list(labels),
        format_func=labels.get,
        key=key,
    )
    return next(item for item in versions if item["selection_version_id"] == selected_id)


def candidate_editor(
    candidates: list[dict[str, Any]],
    existing: list[dict[str, Any]],
    *,
    candidate_type: str,
) -> pd.DataFrame:
    frame = pd.DataFrame(candidates)
    if frame.empty:
        st.warning(f"No {candidate_type} candidates are available")
        return frame
    frame = frame.loc[
        frame["status"].isin(["AVAILABLE", "AVAILABLE_WITH_WARNING"])
    ].copy()
    existing_keys = {_selection_key(candidate_type, row, selected=True) for row in existing}
    frame.insert(
        0,
        "selected",
        [
            _selection_key(candidate_type, row, selected=False) in existing_keys
            for row in frame.to_dict("records")
        ],
    )
    display_columns = _display_columns(candidate_type)
    frame = frame[[column for column in display_columns if column in frame.columns]]
    return st.data_editor(
        frame,
        hide_index=True,
        use_container_width=True,
        disabled=[column for column in frame.columns if column != "selected"],
        column_config={"selected": st.column_config.CheckboxColumn("Select")},
        key=f"{candidate_type}_editor",
    )


def _selection_key(
    candidate_type: str,
    row: dict[str, Any],
    *,
    selected: bool,
) -> tuple[str, ...]:
    common = (
        str(row["triangle_grain"]),
        str(row["development_pool_id"]),
        str(row["measure_type"]),
    )
    if candidate_type == "ldf":
        return common + (
            str(row["from_age_months"]),
            str(row["to_age_months"]),
            str(row["selected_method"] if selected else row["development_method"]),
        )
    if candidate_type == "tail":
        return common + (
            str(row["development_method"]),
            str(
                row["selected_tail_method"] if selected else row["tail_method"]
            ),
        )
    return common + (
        str(row["accident_period"])[:10],
        str(row["development_method"]),
        str(row["tail_method"]),
        str(
            row["selected_ultimate_method"]
            if selected
            else row["ultimate_method"]
        ),
    )


def _display_columns(candidate_type: str) -> list[str]:
    common = [
        "selected",
        "triangle_grain",
        "development_pool_id",
        "pool_level",
        "line_of_business",
        "measure_type",
    ]
    if candidate_type == "ldf":
        return common + [
            "from_age_months",
            "to_age_months",
            "development_method",
            "candidate_ldf",
            "observation_count",
        ]
    if candidate_type == "tail":
        return common + [
            "development_method",
            "tail_method",
            "tail_factor",
            "curve_slope",
            "curve_intercept",
            "bondy_exponent",
        ]
    return common + [
        "accident_period",
        "development_method",
        "tail_method",
        "ultimate_method",
        "latest_observed_value",
        "ultimate_value",
        "ibnr_value",
        "mack_standard_error",
    ]


def _payload(candidate_type: str, frame: pd.DataFrame) -> list[dict[str, Any]]:
    selected = frame.loc[frame["selected"]].to_dict("records")
    payload: list[dict[str, Any]] = []
    for row in selected:
        base = {
            "triangle_grain": row["triangle_grain"],
            "development_pool_id": row["development_pool_id"],
            "pool_level": row.get("pool_level", "development_pool"),
            "line_of_business": row["line_of_business"],
            "measure_type": row["measure_type"],
            "selection_source": "CANDIDATE",
            "selection_reason": None,
        }
        if candidate_type == "ldf":
            base.update(
                from_age_months=int(row["from_age_months"]),
                to_age_months=int(row["to_age_months"]),
                selected_method=row["development_method"],
                selected_ldf=float(row["candidate_ldf"]),
            )
        elif candidate_type == "tail":
            base.update(
                development_method=row["development_method"],
                selected_tail_method=row["tail_method"],
                selected_tail_factor=float(row["tail_factor"]),
            )
        else:
            base.update(
                accident_period=str(row["accident_period"])[:10],
                development_method=row["development_method"],
                tail_method=row["tail_method"],
                selected_ultimate_method=row["ultimate_method"],
                selected_ultimate_value=float(row["ultimate_value"]),
            )
        payload.append(base)
    return payload


if page == "Candidates":
    runs = client.model_runs()
    if not runs:
        st.info("Run the actuarial engine before creating a selection version.")
        st.stop()
    run_labels = {
        item["model_run_id"]: (
            f"{item['as_of_date']} | {item['model_run_id'][:8]} | "
            f"{item['candidate_count']} candidates"
        )
        for item in runs
    }
    model_run_id = st.selectbox(
        "Model run", list(run_labels), format_func=run_labels.get
    )
    candidate_type = st.radio("Candidate type", ["ldf", "tail", "ultimate"], horizontal=True)
    st.dataframe(
        pd.DataFrame(client.candidates(model_run_id, candidate_type)),
        use_container_width=True,
        hide_index=True,
    )
    comment = st.text_input("Draft purpose or scope")
    if st.button("Create draft selection", type="primary"):
        created = client.create_version(model_run_id, comment)
        st.success(f"Created draft {created['selection_version_id']}")

elif page == "Selections":
    versions = client.versions()
    if not versions:
        st.info("Create a draft from the Candidates workspace first.")
        st.stop()
    version = select_version(versions, "selection_version")
    details = client.version(version["selection_version_id"])
    st.write(
        f"Status: **{version['status']}**  |  Model run: `{version['model_run_id']}`"
    )
    tabs = st.tabs(["LDF", "Tail", "Ultimate", "Review"])
    for tab, candidate_type in zip(tabs[:3], ("ldf", "tail", "ultimate"), strict=True):
        with tab:
            candidates = client.candidates(version["model_run_id"], candidate_type)
            edited = candidate_editor(
                candidates,
                details["selections"][candidate_type],
                candidate_type=candidate_type,
            )
            if version["status"] == "DRAFT" and st.button(
                f"Save {candidate_type.upper()} selections",
                key=f"save_{candidate_type}",
            ):
                rows = _payload(candidate_type, edited)
                result = client.save_selections(
                    version["selection_version_id"], candidate_type, rows
                )
                st.success(f"Saved {result['row_count']} rows")
    with tabs[3]:
        for name, rows in details["selections"].items():
            st.subheader(name.upper())
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        submit_comment = st.text_area("Submission comment")
        if version["status"] == "DRAFT" and st.button(
            "Submit for approval", type="primary"
        ):
            submitted = client.action(
                version["selection_version_id"], "submit", submit_comment
            )
            st.success(f"Submitted {submitted['selection_version_id']}")

else:
    versions = client.versions(status="SUBMITTED")
    if not versions:
        st.info("There are no submitted versions waiting for review.")
        st.stop()
    version = select_version(versions, "approval_version")
    details = client.version(version["selection_version_id"])
    for name, rows in details["selections"].items():
        with st.expander(f"{name.upper()} ({len(rows)} rows)", expanded=name == "ultimate"):
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    review_comment = st.text_area("Review comment")
    approve_column, reject_column = st.columns(2)
    with approve_column:
        if st.button("Approve and trigger Airflow", type="primary"):
            result = client.action(
                version["selection_version_id"], "approve", review_comment
            )
            status = result["pipeline_run"]["status"]
            st.success(f"Approved. Downstream trigger status: {status}")
    with reject_column:
        if st.button("Reject"):
            if not review_comment.strip():
                st.error("A rejection comment is required")
            else:
                client.action(
                    version["selection_version_id"], "reject", review_comment
                )
                st.warning("Selection version rejected")
