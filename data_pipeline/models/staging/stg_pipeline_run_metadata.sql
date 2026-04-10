select

    pipeline_run_metadata_id,
    dag_id,
    dag_run_id,
    task_id,
    assumption_set_id,
    assumption_type,
    file_name,
    version_sequence,
    version_label,
    registered_at

from {{ source('actuarial_input', 'pipeline_run_metadata') }}
