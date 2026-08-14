with coverage_month as (

    select *
    from {{ ref('int_coverage_month') }}

),

earned_exposure as (

  select
      coverage_id,
      policy_id,
      risk_unit_id,
      product_id,
      line_of_business,
      primary_state,
      underwriting_tier,
      risk_unit_type,
      exposure_unit,
      coverage_code,
      coverage_family,
      calendar_month,
      exposure_start,
      exposure_end,
      active_days,
      active_days / 365.25 as earned_exposure
  from coverage_month

)

select

    policy_id,
    risk_unit_id,
    coverage_id,
    calendar_month,
    sum(earned_exposure)

from earned_exposure
group by policy_id, risk_unit_id, coverage_id, calendar_month,
