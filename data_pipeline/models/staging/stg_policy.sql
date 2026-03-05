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
    term_months

from {{ source('data', 'policy') }}
