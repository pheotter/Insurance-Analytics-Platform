select

    driver_id,
    policy_id,
    driver_sequence,
    date_of_birth,
    gender,
    years_licensed,
    prior_accidents,
    prior_violations,
    marital_status,
    credit_tier,
    source_system

from {{ source('data', 'raw_driver') }}
