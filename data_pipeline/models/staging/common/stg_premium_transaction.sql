select

    transaction_id,
    policy_id,
    coverage_id,
    transaction_type,
    transaction_date,
    transaction_reason,
    premium_change,
    cumulative_premium,
    source_system

from {{ source('data', 'raw_premium_transaction') }}
