-- models/core/fct_claim.sql
{{ config(
    materialized='incremental',
    unique_key='claim_id',
    incremental_strategy='merge',
    on_schema_change='fail'
) }}

with claims as (

    select *
    from {{ ref('stg_claim') }}

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
    claim_id,
    policy_id,
    risk_unit_id,
    coverage_id,
    loss_date,
    reported_date,
    claim_type,
    cause_code,
    claim_status,
    source_system,
    load_batch_id,
    ingested_at,
    current_timestamp() as processed_at

from claims
