select

    policy_id,
    policy_number,
    insured_id,
    product_id,
    line_of_business,
    effective_date,
    expiration_date,
    cancellation_date,
    status as policy_status,
    underwriting_tier,
    primary_state,
    term_months,
    source_system
    
from {{ source('data', 'raw_policy') }}
