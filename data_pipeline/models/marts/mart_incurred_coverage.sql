with required as (
    select distinct
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        development
    from {{ ref('int_ldf_raw') }}
    where link_ratio_incurred is not null
),

selected as (
    select distinct
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        development
    from {{ ref('int_ldf_selected_incurred') }}
),

joined as (
    select
        coalesce(r.state_grp, s.state_grp) as state_grp,
        coalesce(r.risk_class_grp, s.risk_class_grp) as risk_class_grp,
        coalesce(r.vehicle_segment_grp, s.vehicle_segment_grp) as vehicle_segment_grp,
        coalesce(r.development, s.development) as development,

        case
            when r.development is not null and s.development is not null then 'matched'
            when r.development is not null and s.development is null then 'missing_selected'
            when r.development is null and s.development is not null then 'extra_selected'
        end as status

    from required r
    full outer join selected s
      on r.state_grp = s.state_grp
     and r.risk_class_grp = s.risk_class_grp
     and r.vehicle_segment_grp = s.vehicle_segment_grp
     and r.development = s.development
)

select *
from joined
