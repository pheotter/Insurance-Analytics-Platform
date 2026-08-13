select

    transaction_id,
    claim_id,
    transaction_type,
    transaction_date,
    paid_loss_change,
    case_reserve_change,
    paid_expense_change,
    case_expense_change,
    recovery_change,
    incurred_loss_change,
    source_system

from {{ source('data', 'raw_claim_transaction') }}
