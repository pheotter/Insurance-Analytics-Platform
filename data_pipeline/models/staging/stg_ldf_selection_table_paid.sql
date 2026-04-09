select

    segmentation_version,
    triangle_type,
    state as state_grp,
    risk_class as risk_class_grp,
    vehicle_segment as vehicle_segment_grp,
    development,
    ldf,
    method,
    ay_from,
    ay_to,
    description

from {{ source('actuarial_input', 'ldf_selection_table') }}
where triangle_type = 'paid'
