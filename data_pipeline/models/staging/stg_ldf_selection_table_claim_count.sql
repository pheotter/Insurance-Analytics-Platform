select

    segmentation_version,
    state as state_grp,
    risk_class as risk_class_grp,
    vehicle_segment as vehicle_segment_grp,
    dev as development,
    ldf,
    method,
    ay_from,
    ay_to,
    descriptions

from {{ source('actuarial_input', 'ldf_selection_table')
where triangle_type = "claim_count"
