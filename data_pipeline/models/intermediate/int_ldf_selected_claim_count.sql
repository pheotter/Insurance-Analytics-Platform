with sel as (

    select *
    from {{ ref('stg_ldf_selection_table_claim_count') }}
    where segmentation_version = '{{ var("segmentation_version") }}'

),

avg_ldf as (

    select *
    from {{ ref('int_ldf_avg_claim_count') }}

),

weighted_ldf as (

    select *
    from {{ ref('int_ldf_weighted_claim_count') }}

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
        s.ldf as override_ldf_cnt,

        a.avg_ldf_cnt,
        w.weighted_ldf_cnt,
        l.last3_ldf_cnt

    from sel s

    left join avg_ldf a
        on s.state = a.state_grp
       and s.risk_class = a.risk_class_grp
       and s.vehicle_segment = a.vehicle_segment_grp
       and s.development = a.development

    left join weighted_ldf w
        on s.state = w.state_grp
       and s.risk_class = w.risk_class_grp
       and s.vehicle_segment = w.vehicle_segment_grp
       and s.development = w.development

    left join last3_ldf l
        on s.state = l.state_grp
       and s.risk_class = l.risk_class_grp
       and s.vehicle_segment = l.vehicle_segment_grp
       and s.development = l.development

)

select

    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    development,

    case
        when method = 'avg' then avg_ldf_cnt
        when method = 'weighted' then weighted_ldf_cnt
        when method = 'last3' then last3_ldf_cnt
        when method = 'other' then override_ldf_cnt
    end as selected_ldf_cnt

from combined
