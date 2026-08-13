with sel as (

    select *
    from {{ ref('stg_ldf_selection_table') }}
    where triangle_type = 'incurred'

),

avg_ldf as (

    select *
    from {{ ref('int_ldf_avg') }}

),

weighted_ldf as (

    select *
    from {{ ref('int_ldf_weighted') }}

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
        s.ldf as override_ldf_incurred,

        a.avg_ldf_incurred,
        w.weighted_ldf_incurred,
        l.last3_ldf_incurred

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
        when method = 'avg' then avg_ldf_incurred
        when method = 'weighted' then weighted_ldf_incurred
        when method = 'last3_weighted' then last3_ldf_incurred
        when method = 'other' then override_ldf_incurred
    end as selected_ldf_incurred

from combined
