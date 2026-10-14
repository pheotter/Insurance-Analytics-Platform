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
)

select r.*
from required r
left join selected s
  on r.state_grp = s.state_grp
 and r.risk_class_grp = s.risk_class_grp
 and r.vehicle_segment_grp = s.vehicle_segment_grp
 and r.development = s.development
where s.development is null
