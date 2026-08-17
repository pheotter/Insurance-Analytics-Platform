with earned_exposure  as (

    select

        policy_id,
        risk_unit_id,
        coverage_id,
        calendar_month,
        earned_exposure

    from {{ ref('int_earned_exposure_month') }}

),

coverage_month as (

    select active_days
    from {{ ref('int_coverage_month') }}

),

earned_exposure_total as (

    select

        policy_id,
        risk_unit_id,
        coverage_id,
        sum(earned_exposure)

    from earned_exposure
    group by policy_id, risk_unit_id, coverage_id

),

coverage_month_total as (

    select

        policy_id,
        risk_unit_id,
        coverage_id,
        sum(active_days)

    from coverage_month
    group by policy_id, risk_unit_id, coverage_id

)

select

    policy_id,
    risk_unit_id,
    coverage_id,
    earned_exposure,
    active_days / 365.25

from earned_exposure_total e
join coverage_month_toal c
  on e.policy_id = c.policy_id
 and e.risk_unit_id = c.risk_unit_id
 and e.coverage_id = c.coverage_id
where abs(earned_exposure - active_days / 365.25) > 0.00001
