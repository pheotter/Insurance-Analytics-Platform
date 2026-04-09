with detail as (
    select
        calendar_year,
        sum(total_earned_exposure) as detail_earned_exposure,
        sum(total_earned_premium) as detail_earned_premium
    from {{ ref('int_policy_exposure') }}
    group by 1
),

overall as (
    select
        sum(total_earned_exposure) as overall_exposure,
        sum(total_earned_premium) as overall_earned_premium
    from {{ ref('int_policy_exposure') }}
),

reaggregated as (
    select
        sum(detail_earned_exposure) as reaggregated_exposure,
        sum(detail_earned_premium) as reaggregated_earned_premium
    from detail
)

select
    o.overall_exposure,
    r.reaggregated_exposure,
    o.overall_earned_premium,
    r.reaggregated_earned_premium
from overall o
cross join reaggregated r
where abs(o.overall_exposure - r.reaggregated_exposure) > 0.000001
   or abs(o.overall_earned_premium - r.reaggregated_earned_premium) > 0.000001
