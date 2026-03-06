with trend as (

    select
        segmentation_version,
        trend_type,
        state as state_grp,
        risk_class as risk_class_grp,
        vehicle_segment as vehicle_segment_grp,
        annual_trend,
        effective_from,
        effective_to
    from {{ source('actuarial_input', 'trend_selection') }}

)
