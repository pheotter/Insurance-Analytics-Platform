select

    assumption_set_id,
    assumption_type,
    file_name,
    target_table_name,
    version_sequence,
    version_label,
    status,
    uploaded_at,
    uploaded_by,
    upload_comment,
    source_row_count,
    change_count,
    previous_assumption_set_id,
    dag_id,
    dag_run_id,
    task_id

from {{ source('actuarial_input', 'assumption_version') }}
