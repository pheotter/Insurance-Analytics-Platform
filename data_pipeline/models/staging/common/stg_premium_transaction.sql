select

    cast(transaction_id as varchar) as transaction_id,
    cast(policy_id as varchar) as policy_id,
    cast(coverage_id as varchar) as coverage_id,
    cast(transaction_type as varchar) as transaction_type,
    cast(transaction_date as date) as transaction_date,
    cast(transaction_reason as varchar) as transaction_reason,
    cast(premium_change as number(18, 2)) as premium_change,
    cast(cumulative_premium as number(18, 2)) as cumulative_premium,
    cast(source_system as varchar) as source_system,
    cast(load_batch_id as varchar) as load_batch_id,
    cast(ingested_at as timestamp_ntz) as ingested_at

from {{ source('data', 'raw_premium_transaction') }}
