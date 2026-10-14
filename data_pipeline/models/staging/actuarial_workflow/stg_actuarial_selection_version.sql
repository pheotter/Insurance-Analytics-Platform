select
    selection_version_id,
    model_run_id,
    as_of_date,
    status,
    created_by,
    created_at,
    comment,
    submitted_by,
    submitted_at,
    approved_by,
    approved_at,
    rejected_by,
    rejected_at,
    review_comment,
    row_version

from {{ source('actuarial_workflow', 'selection_version') }}
