with coverage_month as (

    select *
    from {{ ref('int_coverage_month') }}

),

select
    coverage_id,
    policy_id,
    risk_unit_id,

    product_id,
    line_of_business,

    risk_unit_type,
    exposure_unit,
    coverage_code,

    calendar_month,
    exposure_start,
    exposure_end,
    active_days,
    round(active_days / 365.25, 2) as earned_exposure
    
from coverage_month
