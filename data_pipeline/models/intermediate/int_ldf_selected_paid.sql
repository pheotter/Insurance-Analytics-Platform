with sel as (

    select *
    from {{ ref('stg_ldf_selection_table_paid') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'

),

avg_ldf as (

    select *
    from {{ ref('int_ldf_avg_paid') }}

),

weighted_ldf as (

    select *
    from {{ ref('int_ldf_weighted_paid') }}

),

last3_ldf as (

    select *
    from {{ ref('int_ldf_last3_weighted') }}

),

combined as (

    select
        s.state_grp,
        s.risk_class_grp,
        s.vehicle_segment_grp,
        s.development,
        s.method,
        s.ldf as override_ldf_paid,

        a.avg_ldf_paid,
        w.weighted_ldf_paid,
        l.last3_ldf_paid

    from sel s
    join avg_ldf a
        on s.state_grp = a.state_grp
       and s.risk_class_grp = a.risk_class_grp
       and s.vehicle_segment_grp = a.vehicle_segment_grp
       and s.development = a.development

    join weighted_ldf w
        on s.state_grp = w.state_grp
       and s.risk_class_grp = w.risk_class_grp
       and s.vehicle_segment_grp = w.vehicle_segment_grp
       and s.development = w.development

    join last3_ldf l
        on s.state_grp = l.state_grp
       and s.risk_class_grp = l.risk_class_grp
       and s.vehicle_segment_grp = l.vehicle_segment_grp
       and s.development = l.development

)

select

    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    development,

    case
        when method = 'avg' then avg_ldf_paid
        when method = 'weighted' then weighted_ldf_paid
        when method = 'last3_weighted' then last3_ldf_paid
        when method = 'other' then override_ldf_paid
    end as selected_ldf_paid

from combined
