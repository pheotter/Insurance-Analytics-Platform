select
    selection_version_id,
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    measure_type,
    development_method,
    selected_tail_method,
    selected_tail_factor,
    selection_source,
    selection_reason,
    created_by,
    created_at

from {{ source('actuarial_workflow', 'tail_selection') }}
