select

    policy_id,
    policy_number,
    insured_id,
    product_id,
    line_of_business,
    effective_date,
    expiration_date,
    cancellation_date,
    policy_status,
    underwriting_tier,
    primary_state,
    source_system

from {{ ref('stg_policy') }}
