with ordered as (
    select
        *,
        lag(cumulative_paid) over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp, accident_year
            order by development
        ) as prev_cumulative_paid
    from {{ ref('int_claim_triangle_cumulative') }}
)

select *
from ordered
where prev_cumulative_paid is not null
  and cumulative_paid < prev_cumulative_paid
