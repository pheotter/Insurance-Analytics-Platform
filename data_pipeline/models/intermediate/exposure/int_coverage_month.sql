{{ config(
    materialized='incremental',
    unique_key='coverage_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_coverages as (

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

coverage as (

    select *
    from {{ ref('int_coverage_active_period') }}

    {% if is_incremental() %}
    join changed_coverages using (coverage_id)
    {% endif %}

),

months as (

    select *
    from {{ ref('dim_calendar_month') }}

),

expanded as (

    select
        c.coverage_id,
        c.policy_id,
        c.risk_unit_id,
        c.product_id,
        c.line_of_business,
        c.primary_state,
        c.underwriting_tier,
        c.risk_unit_type,
        c.exposure_unit,
        c.coverage_code,
        c.coverage_family,
        c.ingested_at,
        m.month_start as calendar_month,
        greatest(c.coverage_effective_date, m.month_start) as exposure_start,
        least(c.actual_expiration_date, m.next_month_start) as exposure_end
    from coverage c
    join months m
        on m.month_start < c.actual_expiration_date
       and m.next_month_start > c.coverage_effective_date

)

select
    *,
    datediff(day, exposure_start, exposure_end) as active_days,
    current_timestamp() as processed_at
from expanded
