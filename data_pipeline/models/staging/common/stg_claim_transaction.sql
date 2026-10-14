select

    cast(transaction_id as varchar) as transaction_id,
    cast(claim_id as varchar) as claim_id,
    cast(transaction_type as varchar) as transaction_type,
    cast(transaction_date as date) as transaction_date,
    cast(paid_loss_change as number(18, 2)) as paid_loss_change,
    cast(case_reserve_change as number(18, 2)) as case_reserve_change,
    cast(paid_expense_change as number(18, 2)) as paid_expense_change,
    cast(case_expense_change as number(18, 2)) as case_expense_change,
    cast(recovery_change as number(18, 2)) as recovery_change,
    cast(incurred_loss_change as number(18, 2)) as incurred_loss_change,
    cast(source_system as varchar) as source_system,
    cast(load_batch_id as varchar) as load_batch_id,
    cast(ingested_at as timestamp_ntz) as ingested_at

from {{ source('data', 'raw_claim_transaction') }}
