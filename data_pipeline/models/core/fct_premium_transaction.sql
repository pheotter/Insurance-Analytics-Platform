-- models/core/fct_premium_transaction.sql

select
    transaction_id,
    policy_id,
    coverage_id,
    transaction_type,
    transaction_date,
    transaction_reason,
    premium_change,
    cumulative_premium as source_cumulative_premium,
    source_system

from {{ ref('stg_premium_transaction') }}
