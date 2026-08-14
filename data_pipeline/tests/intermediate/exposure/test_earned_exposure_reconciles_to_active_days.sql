select
    coverage_id,
    calendar_month,
    active_days,
    earned_exposure
from {{ ref('int_earned_exposure') }}
where abs(earned_exposure - active_days / 365.25) > 0.0000000001
