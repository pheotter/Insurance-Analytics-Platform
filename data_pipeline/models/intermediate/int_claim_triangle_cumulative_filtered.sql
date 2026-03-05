with triangle as (
    select * from {{ ref('int_claim_triangle_cumulative') }}
),

selection as (
    select * from {{ ref('ldf_selection_table') }}
),

exclusion as (
    select * from {{ ref('ldf_exclusion') }}
)

select
    t.state_grp,
    t.risk_class_grp,
    t.vehicle_segment_grp,
    t.accident_year,
    t.development,
    
    sel.method,
    sel.ay_start,
    sel.ay_end,
    sel.override_factor

from triangle t

join selection sel
    on t.development = sel.development

left join exclusion ex
    on t.accident_year = ex.accident_year
    and t.development = ex.development

where coalesce(ex.exclude_flag,0)=0
  and t.accident_year between sel.ay_start and sel.ay_end
