select
    policy_id,
    risk_unit_id,
    coverage_id,
    calendar_month,
    sum(active_days) / 365.25 as earned_exposure
from {{ ref('int_coverage_month') }}
group by policy_id, risk_unit_id, coverage_id, calendar_month
