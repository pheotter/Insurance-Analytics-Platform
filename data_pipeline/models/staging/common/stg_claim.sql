select

    claim_id,
    policy_id,
    risk_unit_id,
    coverage_id,
    coverage_code,
    loss_date,
    reported_date,
    claim_type,
    cause_code,
    claim_status,
    source_system

from {{ source('data', 'raw_claim') }}
