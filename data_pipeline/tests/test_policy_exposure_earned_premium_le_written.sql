with written_totals as (
    select
        sum(written_premium) as written_premium
    from {{ ref('stg_policy') }}
),

earned_totals as (
    select
        sum(total_earned_premium) as earned_premium
    from {{ ref('int_policy_exposure') }}
)

select
    e.earned_premium,
    w.written_premium
from earned_totals e
cross join written_totals w
where e.earned_premium > w.written_premium
