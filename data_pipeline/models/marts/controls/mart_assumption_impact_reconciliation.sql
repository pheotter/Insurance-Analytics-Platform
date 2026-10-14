with selected_base as (

    select *
    from {{ ref('fct_actuarial_frequency_severity') }}

),

trended as (

    select *
    from {{ ref('fct_pure_premium') }}

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
    b.accident_period,
    b.claim_count_method,
    b.loss_method,
    b.ultimate_claim_count,
    b.ultimate_loss,
    b.frequency,
    b.severity,
    b.pure_premium as untrended_pure_premium,
    t.pure_premium as trended_pure_premium,
    t.pure_premium - b.pure_premium as trend_impact_on_pure_premium,
    i.indicated_premium,
    i.indicated_premium - t.pure_premium as expense_profit_impact

from selected_base b
left join trended t
  on b.selection_version_id = t.selection_version_id
 and b.triangle_grain = t.triangle_grain
 and b.development_pool_id = t.development_pool_id
 and b.line_of_business = t.line_of_business
 and b.accident_period = t.accident_period
left join indicated i
  on b.selection_version_id = i.selection_version_id
 and b.triangle_grain = i.triangle_grain
 and b.development_pool_id = i.development_pool_id
 and b.line_of_business = i.line_of_business
