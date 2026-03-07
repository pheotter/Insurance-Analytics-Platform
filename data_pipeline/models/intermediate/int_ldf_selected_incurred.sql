with sel as (

    select *
    from {{ ref('stg_ldf_selection_table_incurred') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'

),

avg_ldf as (

    select *
    from {{ ref('int_ldf_avg_incurred') }}

),

weighted_ldf as (

    select *
    from {{ ref('int_ldf_weighted_incurred') }}

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
        s.ldf as override_ldf,

        a.avg_ldf,
        w.weighted_ldf,
        l.last3_ldf

    from sel s
    left join avg_ldf a
        on s.state_grp = a.state_grp
       and s.risk_class_grp = a.risk_class_grp
       and s.vehicle_segment_grp = a.vehicle_segment_grp
       and s.development = a.development

    left join weighted_ldf w
        on s.state_grp = w.state_grp
       and s.risk_class_grp = w.risk_class_grp
       and s.vehicle_segment_grp = w.vehicle_segment_grp
       and s.development = w.development

    left join last3_ldf l
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
        when method = 'avg' then avg_ldf
        when method = 'weighted' then weighted_ldf
        when method = 'last3' then last3_ldf
        when method = 'other' then override_ldf
    end as selected_ldf

from combined
