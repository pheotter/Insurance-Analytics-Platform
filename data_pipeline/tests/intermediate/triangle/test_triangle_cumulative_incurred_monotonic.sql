{{ config(severity='warn') }}

with ordered as (
    select
        *,
        lag(cumulative_incurred) over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp, accident_year
            order by development
        ) as prev_cumulative_incurred
    from {{ ref('int_claim_triangle_cumulative') }}
)

select *
from ordered
where prev_cumulative_incurred is not null
  and cumulative_incurred < prev_cumulative_incurred * 0.9
