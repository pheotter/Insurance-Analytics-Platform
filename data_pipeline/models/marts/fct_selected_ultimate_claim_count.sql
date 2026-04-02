with selection as (

    select *
    from {{ ref('stg_ultimate_selection_claim_count') }}

),

candidates as (

    select *
    from {{ ref('fct_ultimate_claim_count') }}

)

select
    s.segmentation_version,
    s.state_grp,
    s.risk_class_grp,
    s.vehicle_segment_grp,
    s.accident_year,
    c.ultimate_claim_count,
    s.selected_method as method,
    s.comment
from selection s
join candidates c
  on s.state_grp = c.state_grp
 and s.risk_class_grp = c.risk_class_grp
 and s.vehicle_segment_grp = c.vehicle_segment_grp
 and s.accident_year = c.accident_year
 and s.selected_method = c.method
