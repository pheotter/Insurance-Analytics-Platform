select

    risk_unit_id,
    policy_id,
    risk_unit_type,
    source_risk_unit_id,
    effective_date,
    expiration_date,
    status as policy_risk_unit_status,
    exposure_unit,
    source_system

from {{ source('data', 'raw_policy_risk_unit') }}
