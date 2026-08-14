with expected as (

    select
        coverage_id,
        sum(premium_change) as net_written_premium
    from {{ ref('stg_premium_transaction') }}
    group by coverage_id

),

actual as (

    select
        coverage_id,
        sum(earned_premium) as earned_premium
    from {{ ref('int_earned_premium_month') }}
    group by coverage_id

)

select
    coalesce(e.coverage_id, a.coverage_id) as coverage_id,
    coalesce(e.net_written_premium, 0) as net_written_premium,
    coalesce(a.earned_premium, 0) as earned_premium
from expected e
full outer join actual a
    on e.coverage_id = a.coverage_id
where abs(
    coalesce(e.net_written_premium, 0)
    - coalesce(a.earned_premium, 0)
) > 0.02
