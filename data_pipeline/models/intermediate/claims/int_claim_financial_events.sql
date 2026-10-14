{{ config(
    materialized='incremental',
    unique_key='claim_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_claims as (

    select distinct claim_id
    from {{ ref('fct_claim_transaction') }}

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

    union

    select distinct claim_id
    from {{ ref('fct_claim') }}

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

),

reported_anchor as (

    select
        claim_id || '-REPORTED_ANCHOR' as event_id,
        claim_id,
        cast(null as varchar) as source_transaction_id,
        reported_date as event_date,

        0::number as paid_loss_change,
        0::number as case_reserve_change,
        0::number as paid_expense_change,
        0::number as case_expense_change,
        0::number as recovery_change,
        0::number as incurred_loss_change,

        'REPORTED_ANCHOR' as event_type,
        load_batch_id,
        ingested_at

    from {{ ref('fct_claim') }}

    {% if is_incremental() %}
    join changed_claims using (claim_id)
    {% endif %}

),

financial_transactions as (

    select
        'FINANCIAL_TRANSACTION-' || transaction_id as event_id,
        claim_id,
        transaction_id as source_transaction_id,
        transaction_date as event_date,

        paid_loss_change,
        case_reserve_change,
        paid_expense_change,
        case_expense_change,
        recovery_change,
        incurred_loss_change,

        'FINANCIAL_TRANSACTION' as event_type,
        load_batch_id,
        ingested_at

    from {{ ref('fct_claim_transaction') }}

    {% if is_incremental() %}
    join changed_claims using (claim_id)
    {% endif %}

),

all_events as (

    select * from reported_anchor

    union all

    select * from financial_transactions

)

select *
    , current_timestamp() as processed_at
from all_events
