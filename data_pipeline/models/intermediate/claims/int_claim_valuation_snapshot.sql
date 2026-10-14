-- models/intermediate/claims/int_claim_valuation_snapshot.sql
{{ config(
    materialized='incremental',
    unique_key='claim_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

with changed_claims as (

    select distinct claim_id
    from {{ ref('int_claim_financial_state_period') }}

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

valuation_dates as (

    select
        valuation_date,
        valuation_month,

        calendar_year,
        calendar_quarter,
        calendar_month,

        is_quarter_end,
        is_half_year_end,
        is_year_end

    from {{ ref('int_valuation_dates') }}

),

claim_states as (

    select
        claim_id,

        valid_from_date,
        valid_to_date,
        is_current_state,
        is_reported_only_state,
        has_financial_activity,

        cumulative_financial_transaction_count,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss,

        calculated_cumulative_incurred,
        latest_event_ingested_at

    from {{ ref('int_claim_financial_state_period') }}

    {% if is_incremental() %}
    join changed_claims using (claim_id)
    {% endif %}

),

claims as (

    select
        claim_id,
        policy_id,
        risk_unit_id,
        coverage_id,

        loss_date,
        reported_date,

        claim_type,
        cause_code

    from {{ ref('fct_claim') }}

),

policies as (

    select
        policy_id,
        product_id,
        line_of_business

    from {{ ref('dim_policy') }}

),

coverages as (

    select
        coverage_id,
        coverage_code

    from {{ ref('dim_coverage') }}

),

snapshots as (

    select
        v.valuation_date,
        v.valuation_month,

        v.calendar_year,
        v.calendar_quarter,
        v.calendar_month,

        v.is_quarter_end,
        v.is_half_year_end,
        v.is_year_end,

        c.claim_id,
        c.policy_id,
        c.risk_unit_id,
        c.coverage_id,

        p.product_id,
        p.line_of_business,
        cov.coverage_code,

        c.loss_date,
        c.reported_date,
        c.claim_type,
        c.cause_code,

        s.is_reported_only_state,
        s.has_financial_activity,
        s.cumulative_financial_transaction_count,

        s.cumulative_paid_loss,
        s.cumulative_case_reserve,
        s.cumulative_paid_expense,
        s.cumulative_case_expense,
        s.cumulative_recovery,
        s.cumulative_incurred_loss,

        s.calculated_cumulative_incurred,
        s.latest_event_ingested_at,
        current_timestamp() as processed_at

    from claim_states s

    join valuation_dates v
      on v.valuation_date >= s.valid_from_date
     and v.valuation_date < s.valid_to_date

    join claims c
      on s.claim_id = c.claim_id

    join policies p
      on c.policy_id = p.policy_id

    join coverages cov
      on c.coverage_id = cov.coverage_id

)

select *
from snapshots
