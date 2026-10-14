{{ config(
    materialized='incremental',
    unique_key='coverage_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_coverages as (

    select distinct coverage_id
    from {{ ref('fct_premium_transaction') }}

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

    select distinct coverage_id
    from {{ ref('int_coverage_active_period') }}

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

premium_transactions as (

    select

        transaction_id,
        policy_id,
        coverage_id,
        transaction_type,
        transaction_date as earning_start_date,
        premium_change,
        load_batch_id,
        ingested_at

    from {{ ref('fct_premium_transaction') }}

    {% if is_incremental() %}
    join changed_coverages using (coverage_id)
    {% endif %}

),

coverage as (

    select

        coverage_id,
        coverage_effective_date,
        scheduled_expiration_date,
        actual_expiration_date,
        ingested_at

    from {{ ref('int_coverage_active_period') }}

),

earning_segments as (

    select
        t.transaction_id,
        t.policy_id,
        t.coverage_id,
        t.transaction_type,
        t.earning_start_date,
        c.scheduled_expiration_date as scheduled_earning_end_date,
        least(
            c.actual_expiration_date,
            c.scheduled_expiration_date
        ) as earning_end_date,
        t.premium_change,
        t.load_batch_id,
        greatest(t.ingested_at, c.ingested_at) as ingested_at,

        datediff(
            day,
            t.earning_start_date,
            c.scheduled_expiration_date
        ) as scheduled_earning_days,

        datediff(
            day,
            t.earning_start_date,
            least(
                c.actual_expiration_date,
                c.scheduled_expiration_date
            )
        ) as earning_days

    from premium_transactions t
    join coverage c
        on t.coverage_id = c.coverage_id

    where t.earning_start_date < least(
        c.actual_expiration_date,
        c.scheduled_expiration_date
    )

)

select *
    , current_timestamp() as processed_at
from earning_segments
