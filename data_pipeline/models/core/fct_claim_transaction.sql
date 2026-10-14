-- models/core/fct_claim_transaction.sql
{{ config(
    materialized='incremental',
    unique_key='transaction_id',
    incremental_strategy='merge',
    on_schema_change='fail'
) }}

with claim_transactions as (

    select *
    from {{ ref('stg_claim_transaction') }}

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
    claim_id,
    transaction_type,
    transaction_date,
    paid_loss_change,
    case_reserve_change,
    paid_expense_change,
    case_expense_change,
    recovery_change,
    incurred_loss_change,
    source_system,
    load_batch_id,
    ingested_at,
    current_timestamp() as processed_at

from claim_transactions
