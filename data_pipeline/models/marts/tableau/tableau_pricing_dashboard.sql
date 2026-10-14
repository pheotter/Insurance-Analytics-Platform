with rate_change as (

    select *
    from {{ ref('mart_indicated_rate_change_pure_premium') }}

),

movement as (

    select *
    from {{ ref('mart_reserve_pricing_movement_attribution') }}

),

controls as (

    select
        case
            when count_if(control_status = 'FAIL') > 0 then 'FAIL'
            when count_if(control_status = 'WARN') > 0 then 'WARN'
            else 'PASS'
        end as control_status,
        count_if(control_status = 'FAIL') as failed_control_count,
        count_if(control_status = 'WARN') as warning_control_count
    from {{ ref('mart_control_tolerance_by_metric') }}

)

select
    r.selection_version_id,
    r.triangle_grain,
    r.development_pool_id,
    r.pool_level,
    r.line_of_business,
    r.pricing_version,
    r.first_accident_period,
    r.latest_accident_period,
    r.earned_exposure,
    r.earned_premium,
    r.current_average_premium,
    r.untrended_pure_premium,
    r.pure_premium as trended_pure_premium,
    r.indicated_premium,
    r.target_loss_ratio_premium,
    r.indicated_rate_change,
    r.target_loss_ratio_rate_change,
    m.trend_impact_on_pure_premium,
    m.expense_and_profit_impact,
    c.control_status,
    c.failed_control_count,
    c.warning_control_count

from rate_change r
left join movement m
  on r.selection_version_id = m.selection_version_id
 and r.triangle_grain = m.triangle_grain
 and r.development_pool_id = m.development_pool_id
 and r.line_of_business = m.line_of_business
cross join controls c
