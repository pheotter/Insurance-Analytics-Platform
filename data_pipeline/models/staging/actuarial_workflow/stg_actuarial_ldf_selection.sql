select
    selection_version_id,
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    measure_type,
    from_age_months,
    to_age_months,
    selected_method,
    selected_ldf,
    selection_source,
    selection_reason,
    created_by,
    created_at

from {{ source('actuarial_workflow', 'ldf_selection') }}
