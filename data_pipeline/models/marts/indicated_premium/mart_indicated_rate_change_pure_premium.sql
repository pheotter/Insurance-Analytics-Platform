with indicated as (

    select *
    from {{ ref('fct_indicated_premium') }}

)

select
    selection_version_id,
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    pricing_version,
    first_accident_period,
    latest_accident_period,
    earned_exposure,
    earned_premium,
    current_average_premium,
    untrended_pure_premium,
    pure_premium,
    indicated_premium,
    target_loss_ratio_premium,
    indicated_premium / nullif(current_average_premium, 0) - 1
        as indicated_rate_change,
    target_loss_ratio_premium / nullif(current_average_premium, 0) - 1
        as target_loss_ratio_rate_change

from indicated
