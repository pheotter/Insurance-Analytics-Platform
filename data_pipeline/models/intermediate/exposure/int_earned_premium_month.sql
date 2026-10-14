{{ config(
    materialized='incremental',
    unique_key='coverage_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_coverages as (

    select distinct coverage_id
    from {{ ref('int_premium_earning_segments') }}

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

earning_segments as (

    select

        transaction_id,
        policy_id,
        coverage_id,
        transaction_type,
        earning_start_date,
        earning_end_date,
        premium_change,
        scheduled_earning_days,
        earning_days,
        ingested_at

    from {{ ref('int_premium_earning_segments')}}

    {% if is_incremental() %}
    join changed_coverages using (coverage_id)
    {% endif %}

),

months as (

    select
    
        month_start,
        next_month_start

    from {{ ref('dim_calendar_month') }}

),

expanded as (

    select

        e.transaction_id,
        e.policy_id,
        e.coverage_id,
        e.transaction_type,
        e.premium_change,
        e.ingested_at,

        m.month_start as calendar_month,

        greatest(
            e.earning_start_date,
            m.month_start
        ) as earning_start_in_month,

        least(
            e.earning_end_date,
            m.next_month_start
        ) as earning_end_in_month,

        e.earning_days
            as earning_days,

        e.scheduled_earning_days

    from earning_segments e
    join months m
        on m.month_start < e.earning_end_date
       and m.next_month_start > e.earning_start_date

),

monthly as (

    select
        *,

        datediff(
            day,
            earning_start_in_month,
            earning_end_in_month
        ) as earned_days_in_month

    from expanded

)

select

    policy_id,
    coverage_id,
    calendar_month,

    sum(
        premium_change
        * earned_days_in_month
        / nullif(scheduled_earning_days, 0)
    ) as earned_premium,
    max(ingested_at) as ingested_at,
    current_timestamp() as processed_at

from monthly
group by policy_id, coverage_id, calendar_month
