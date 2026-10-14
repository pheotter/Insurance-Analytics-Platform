select
    selection_version_id,
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    measure_type,
    accident_period,
    development_method,
    tail_method,
    selected_ultimate_method,
    selected_ultimate_value,
    selection_source,
    selection_reason,
    created_by,
    created_at

from {{ source('actuarial_workflow', 'ultimate_selection') }}
