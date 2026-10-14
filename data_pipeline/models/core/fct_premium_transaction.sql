-- models/core/fct_premium_transaction.sql
{{ config(
    materialized='incremental',
    unique_key='transaction_id',
    incremental_strategy='merge',
    on_schema_change='fail'
) }}

with premium_transactions as (

    select *
    from {{ ref('stg_premium_transaction') }}

    {% if is_incremental() %}
    where ingested_at >= dateadd(
        day,
        -{{ var('incremental_lookback_days', 7) }},
        (
            select coalesce(max(ingested_at), to_timestamp_ntz('1900-01-01'))
            from {{ this }}
        )
    )
    {% endif %}

)

select
    transaction_id,
    policy_id,
    coverage_id,
    transaction_type,
    transaction_date,
    transaction_reason,
    premium_change,
    cumulative_premium as source_cumulative_premium,
    source_system,
    load_batch_id,
    ingested_at,
    current_timestamp() as processed_at

from premium_transactions
