select
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    accident_period,
    development_age_months,
    valuation_date,
    cumulative_reported_claim_count,
    cumulative_paid_loss,
    cumulative_paid_expense,
    cumulative_case_reserve,
    cumulative_case_expense,
    cumulative_recovery,
    cumulative_incurred_loss,
    cumulative_paid_loss + cumulative_paid_expense as cumulative_paid_and_expense,
    cumulative_paid_loss
        + cumulative_case_reserve
        + cumulative_paid_expense
        + cumulative_case_expense
        - cumulative_recovery
        as calculated_cumulative_incurred

from {{ ref('int_loss_triangle_pooled') }}
