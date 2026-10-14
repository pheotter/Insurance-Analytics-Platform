-- models/intermediate/claims/int_claim_state_period.sql
{{ config(
    materialized='incremental',
    unique_key='claim_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_claims as (

    select distinct claim_id
    from {{ ref('int_claim_financial_state_cumulative') }}

    {% if is_incremental() %}
    where latest_event_ingested_at >= dateadd(
        day,
        -{{ var('incremental_lookback_days', 7) }},
        (
            select coalesce(max(latest_event_ingested_at), to_timestamp_ntz('1900-01-01'))
            from {{ this }}
        )
    )
    {% endif %}

),

cumulative as (

    select
        claim_id,
        event_date,

        cumulative_financial_transaction_count,
        has_financial_activity,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss,

        calculated_cumulative_incurred,
        latest_event_ingested_at

    from {{ ref('int_claim_financial_state_cumulative') }}

    {% if is_incremental() %}
    join changed_claims using (claim_id)
    {% endif %}

),

with_next_event as (

    select
        *,

        lead(event_date) over (
            partition by claim_id
            order by event_date
        ) as next_event_date

    from cumulative

)

select
    claim_id,

    event_date as valid_from_date,

    coalesce(
        next_event_date,
        date '9999-12-31'
    ) as valid_to_date,

    case
        when next_event_date is null
        then true
        else false
    end as is_current_state,

    cumulative_financial_transaction_count,

    case
        when cumulative_financial_transaction_count = 0
        then true
        else false
    end as is_reported_only_state,

    has_financial_activity,

    cumulative_paid_loss,
    cumulative_case_reserve,
    cumulative_paid_expense,
    cumulative_case_expense,
    cumulative_recovery,
    cumulative_incurred_loss,

    calculated_cumulative_incurred,
    latest_event_ingested_at,
    current_timestamp() as processed_at

from with_next_event
