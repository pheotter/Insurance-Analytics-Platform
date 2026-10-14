{{ config(
    materialized='incremental',
    unique_key='coverage_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_coverages as (

    select distinct coverage_id
    from {{ ref('int_earned_exposure_month') }}

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
    from {{ ref('int_earned_premium_month') }}

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

exposure as (

    select *
    from {{ ref('int_earned_exposure_month') }}

    {% if is_incremental() %}
    join changed_coverages using (coverage_id)
    {% endif %}

),

premium as (

    select *
    from {{ ref('int_earned_premium_month') }}

    {% if is_incremental() %}
    join changed_coverages using (coverage_id)
    {% endif %}

),

policy as (

    select *
    from {{ ref('dim_policy') }}

),

risk_unit as (

    select *
    from {{ ref('dim_risk_unit') }}

),

coverage as (

    select *
    from {{ ref('dim_coverage') }}

)


select

    {{ dbt_utils.generate_surrogate_key([
        'e.risk_unit_id',
        'e.coverage_id',
        'e.calendar_month'
    ]) }} as exposure_id,

    e.policy_id,
    e.risk_unit_id,
    e.coverage_id,
    e.calendar_month,

    p.product_id,
    p.line_of_business,

    r.risk_unit_type,
    r.exposure_unit,

    c.coverage_code,
    c.coverage_family,

    e.earned_exposure,

    coalesce(
        pr.earned_premium,
        0
    ) as earned_premium,

    greatest(
        e.ingested_at,
        coalesce(pr.ingested_at, e.ingested_at)
    ) as ingested_at,
    current_timestamp() as processed_at

from exposure e
left join premium pr
    on e.coverage_id = pr.coverage_id
   and e.calendar_month = pr.calendar_month

join policy p
    on e.policy_id = p.policy_id

join risk_unit r
    on e.risk_unit_id = r.risk_unit_id
    
join coverage c
    on e.coverage_id = c.coverage_id
