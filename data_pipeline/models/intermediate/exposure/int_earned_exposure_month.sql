{{ config(
    materialized='incremental',
    unique_key='coverage_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_coverages as (

    select distinct coverage_id
    from {{ ref('int_coverage_month') }}

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

coverage_months as (

    select *
    from {{ ref('int_coverage_month') }}

    {% if is_incremental() %}
    join changed_coverages using (coverage_id)
    {% endif %}

)

select
    policy_id,
    risk_unit_id,
    coverage_id,
    calendar_month,
    sum(active_days) / 365.25 as earned_exposure,
    max(ingested_at) as ingested_at,
    current_timestamp() as processed_at
from coverage_months
group by policy_id, risk_unit_id, coverage_id, calendar_month
