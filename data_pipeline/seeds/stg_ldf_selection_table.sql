select

    segmentation_version,
    triangle_type,
    state as state_grp,
    risk_class as risk_class_grp,
    vehicle_segment as vehicle_segment_grp,
    development,
    ldf,
    method,
    description

from {{ source('actuarial_input', 'ldf_selection_table') }}
where segmentation_version = '{{ var("segmentation_version", "v3") }}'
