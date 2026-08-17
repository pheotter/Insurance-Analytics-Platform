with expected as (

    select
        coverage_id,
        sum(
            premium_change
            * earning_days
            / nullif(earning_end_date - earning_start_date, 0)
        ) as expected_earned_premium
    from {{ ref('int_premium_earning_segments') }}
    group by coverage_id

),

actual as (

    select
        coverage_id,
        sum(earned_premium) as actual_earned_premium
    from {{ ref('int_earned_premium_month') }}
    group by coverage_id

)

select
    coalesce(e.coverage_id, a.coverage_id) as coverage_id,
    coalesce(e.expected_earned_premium, 0) as expected_earned_premium,
    coalesce(a.actual_earned_premium, 0) as actual_earned_premium
from expected e
full outer join actual a
    on e.coverage_id = a.coverage_id
where abs(
    coalesce(e.expected_earned_premium, 0)
    - coalesce(a.actual_earned_premium, 0)
) > 0.01
