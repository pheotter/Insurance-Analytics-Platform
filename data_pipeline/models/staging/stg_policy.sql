select

    policy_id,
    state,
    risk_class,
    vehicle_segment,
    effective_date,
    expiration_date,
    cancellation_date,
    status as policy_status,
    written_premium,
    term_months,
    vehicle_year,
    driver_age,
    credit_score_band

from {{ source('data', 'dim_policy') }}
