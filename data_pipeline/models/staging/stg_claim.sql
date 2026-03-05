select

    claim_id,
    policy_id,
    loss_date as accident_date,
    transaction_date,
    incremental_paid,
    cumulative_paid,
    case_reserve,
    incurred,
    status as claim_status

from {{ source('data', 'claim') }}
