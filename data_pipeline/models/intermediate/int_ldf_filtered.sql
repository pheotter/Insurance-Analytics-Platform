with link as (
    select * from {{ ref('int_ldf_raw') }}
),

selection as (
    select * from {{ ref('ldf_selection_table') }}
),

exclusion as (
    select * from {{ ref('ldf_exclusion') }}
)

select
    lk.state_grp,
    lk.risk_class_grp,
    lk.vehicle_segment_grp,
    lk.driver_age_grp,
    lk.credit_score_band_grp,
    lk.accident_year,
    lk.development,
    lk.link_ratio,
    sel.method,
    sel.ay_start,
    sel.ay_end,
    sel.override_factor

from link lk

join selection sel
    on lk.development = sel.development

left join exclusion ex
    on lk.accident_year = ex.accident_year
    and lk.development = ex.development

where coalesce(ex.exclude_flag,0)=0
  and lk.accident_year between sel.ay_start and sel.ay_end
