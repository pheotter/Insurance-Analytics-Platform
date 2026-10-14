{{ config(
    materialized='incremental',
    unique_key='coverage_id',
    incremental_strategy='merge',
    on_schema_change='fail'
) }}

with coverage as (

    select *
    from {{ ref('stg_policy_coverage') }}

),

policy as (

    select *
    from {{ ref('stg_policy') }}

),

risk_unit as (

    select *
    from {{ ref('stg_policy_risk_unit') }}

),

joined as (

    select
        c.coverage_id,
        c.policy_id,
        c.risk_unit_id,

        p.product_id,
        p.line_of_business,

        r.risk_unit_type,
        r.exposure_unit,

        c.coverage_code,
        c.coverage_family,
        p.primary_state,
        p.underwriting_tier,
        c.written_premium,

        greatest(
            c.effective_date,
            p.effective_date,
            r.effective_date
        ) as coverage_effective_date,

        c.expiration_date as scheduled_expiration_date,

        least(
            c.expiration_date,
            p.expiration_date,
            r.expiration_date,
            coalesce(
                p.cancellation_date,
                c.expiration_date
            )
        ) as actual_expiration_date,

        c.load_batch_id,
        greatest(
            c.ingested_at,
            p.ingested_at,
            r.ingested_at
        ) as ingested_at

    from coverage c
    join policy p
        on c.policy_id = p.policy_id
    join risk_unit r
        on c.risk_unit_id = r.risk_unit_id

    {% if is_incremental() %}
    where greatest(c.ingested_at, p.ingested_at, r.ingested_at) >= dateadd(
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
    *,
    current_timestamp() as processed_at
from joined
