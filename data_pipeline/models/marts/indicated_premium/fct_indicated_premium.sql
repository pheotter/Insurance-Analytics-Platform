with base as (

    select *
    from {{ ref('fct_pure_premium') }}

),

expense_global as (

    select
        max(pricing_version) as pricing_version,
        avg(fixed_expense_per_exposure) as fixed_expense_per_exposure,
        avg(variable_expense_ratio) as variable_expense_ratio,
        avg(ulae_ratio) as ulae_ratio,
        avg(profit_ratio) as profit_ratio,
        avg(target_loss_ratio) as target_loss_ratio
    from {{ ref('stg_expense_assumption') }}

),

pooled as (

    select
        selection_version_id,
        triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        sum(earned_exposure) as earned_exposure,
        sum(earned_premium) as earned_premium,
        sum(ultimate_claim_count) as ultimate_claim_count,
        sum(ultimate_loss) as ultimate_loss,
        sum(pure_premium * earned_exposure)
            / nullif(sum(earned_exposure), 0) as pure_premium,
        sum(untrended_pure_premium * earned_exposure)
            / nullif(sum(earned_exposure), 0) as untrended_pure_premium,
        min(accident_period) as first_accident_period,
        max(accident_period) as latest_accident_period
    from base
    group by
        selection_version_id,
        triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business

)

select
    p.selection_version_id,
    p.triangle_grain,
    p.development_pool_id,
    p.pool_level,
    p.line_of_business,
    p.first_accident_period,
    p.latest_accident_period,
    e.pricing_version,
    p.earned_exposure,
    p.earned_premium,
    p.ultimate_claim_count,
    p.ultimate_loss,
    p.untrended_pure_premium,
    p.pure_premium,
    e.fixed_expense_per_exposure,
    e.variable_expense_ratio,
    e.ulae_ratio,
    e.profit_ratio,
    e.target_loss_ratio,
    p.earned_premium / nullif(p.earned_exposure, 0) as current_average_premium,
    (
        p.pure_premium * (1 + coalesce(e.ulae_ratio, 0))
        + coalesce(e.fixed_expense_per_exposure, 0)
    )
    / nullif(
        1
        - coalesce(e.variable_expense_ratio, 0)
        - coalesce(e.profit_ratio, 0),
        0
    ) as indicated_premium,
    p.pure_premium / nullif(e.target_loss_ratio, 0) as target_loss_ratio_premium

from pooled p
cross join expense_global e
