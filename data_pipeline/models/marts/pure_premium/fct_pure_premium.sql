select
    selection_version_id,
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    accident_period,
    earned_exposure,
    earned_premium,
    ultimate_claim_count,
    ultimate_loss,
    claim_count_method,
    loss_method,
    trended_frequency,
    trended_severity,
    trended_frequency * trended_severity as pure_premium,
    untrended_pure_premium,
    frequency_annual_trend,
    severity_annual_trend,
    frequency_trend_years,
    severity_trend_years

from {{ ref('fct_frequency_severity_trended') }}
