with monthly as (

    select
        coverage_id,
        sum(active_days) as monthly_active_days
    from {{ ref('int_coverage_month') }}
    group by coverage_id

),

active_period as (

    select
        coverage_id,
        datediff(day, coverage_effective_date, actual_expiration_date) as expected_active_days
    from {{ ref('int_coverage_active_period') }}

)

select
    a.coverage_id,
    a.expected_active_days,
    coalesce(m.monthly_active_days, 0) as monthly_active_days
from active_period a
left join monthly m
    on a.coverage_id = m.coverage_id
where a.expected_active_days != coalesce(m.monthly_active_days, 0)
