select

    assumption_set_id,
    assumption_type,
    file_name,
    row_key,
    change_type,
    column_name,
    old_value,
    new_value,
    changed_at

from {{ source('actuarial_input', 'assumption_change_log') }}
