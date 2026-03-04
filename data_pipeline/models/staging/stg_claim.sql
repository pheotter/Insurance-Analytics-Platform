select

    claim_id,
    policy_id,
    claim_type,
    loss_date as accident_date,
    report_date,
    close_date,
    status as claim_status,
    paid_loss,
    case_reserve,
    incurred_loss

from {{ source('data', 'fact_claim') }}
