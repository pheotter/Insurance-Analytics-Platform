-- Compatibility mart name for downstream models that historically consumed
-- fct_frequency_severity. The canonical versioned output is
-- fct_actuarial_frequency_severity.

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
    frequency,
    severity,
    pure_premium

from {{ ref('fct_actuarial_frequency_severity') }}
