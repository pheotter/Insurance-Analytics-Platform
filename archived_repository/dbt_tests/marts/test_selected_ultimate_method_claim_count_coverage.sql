with required as (
    select distinct
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year
    from {{ ref('fct_ultimate_claim_count') }}
),

selected as (
    select distinct
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year
    from {{ ref('stg_ultimate_selection_claim_count') }}
)

select r.*
from required r
left join selected s
  on r.state_grp = s.state_grp
 and r.risk_class_grp = s.risk_class_grp
 and r.vehicle_segment_grp = s.vehicle_segment_grp
 and r.accident_year = s.accident_year
where s.accident_year is null
