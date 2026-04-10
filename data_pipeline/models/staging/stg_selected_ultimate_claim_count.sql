select

    segmentation_version,
    state as state_grp,
    risk_class as risk_class_grp,
    vehicle_segment as vehicle_segment_grp,
    accident_year,
    ultimate as ultimate_claim_count,
    method,
    comment

from {{ source('actuarial_input', 'selected_ultimate') }}
where type = 'claim_count'
and segmentation_version = '{{ var("segmentation_version", "v3") }}'
