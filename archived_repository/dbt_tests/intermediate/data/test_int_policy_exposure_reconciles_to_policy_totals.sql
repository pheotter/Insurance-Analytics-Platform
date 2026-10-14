with policy_totals as (

    select
        sum(written_premium) as expected_written_premium,
        sum(term_months / 12.0) as expected_exposure
    from {{ ref('stg_policy') }}

),

exposure_totals as (

    select
        sum(total_earned_premium) as actual_earned_premium,
        sum(total_earned_exposure) as actual_earned_exposure
    from {{ ref('int_policy_exposure') }}

)

select
    p.expected_written_premium,
    e.actual_earned_premium,
    p.expected_exposure,
    e.actual_earned_exposure
from policy_totals p
cross join exposure_totals e
where coalesce(p.expected_written_premium, 0) < coalesce(e.actual_earned_premium, 0)
   or coalesce(p.expected_exposure, 0) < coalesce(e.actual_earned_exposure, 0)
