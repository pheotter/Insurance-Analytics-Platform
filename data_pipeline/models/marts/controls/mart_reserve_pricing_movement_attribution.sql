with base as (

    select
        selection_version_id,
        triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        sum(pure_premium * earned_exposure) / nullif(sum(earned_exposure), 0)
            as untrended_pure_premium,
        sum(earned_exposure) as earned_exposure,
        sum(earned_premium) as earned_premium
    from {{ ref('fct_actuarial_frequency_severity') }}
    group by
        selection_version_id,
        triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business

),

trended as (

    select
        selection_version_id,
        triangle_grain,
        development_pool_id,
        line_of_business,
        sum(pure_premium * earned_exposure) / nullif(sum(earned_exposure), 0)
            as trended_pure_premium
    from {{ ref('fct_pure_premium') }}
    group by
        selection_version_id,
        triangle_grain,
        development_pool_id,
        line_of_business

),

indicated as (

    select *
    from {{ ref('fct_indicated_premium') }}

)

select
    b.selection_version_id,
    b.triangle_grain,
    b.development_pool_id,
    b.pool_level,
    b.line_of_business,
    b.earned_exposure,
    b.earned_premium,
    b.untrended_pure_premium,
    t.trended_pure_premium,
    t.trended_pure_premium - b.untrended_pure_premium
        as trend_impact_on_pure_premium,
    i.indicated_premium,
    i.indicated_premium - t.trended_pure_premium
        as expense_and_profit_impact,
    i.current_average_premium,
    i.indicated_premium / nullif(i.current_average_premium, 0) - 1
        as indicated_rate_change
from base b
left join trended t
  on b.selection_version_id = t.selection_version_id
 and b.triangle_grain = t.triangle_grain
 and b.development_pool_id = t.development_pool_id
 and b.line_of_business = t.line_of_business
left join indicated i
  on b.selection_version_id = i.selection_version_id
 and b.triangle_grain = i.triangle_grain
 and b.development_pool_id = i.development_pool_id
 and b.line_of_business = i.line_of_business
