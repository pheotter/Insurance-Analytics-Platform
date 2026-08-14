select

    risk_unit_id,
    policy_id,
    risk_unit_type,
    source_risk_unit_id,
    effective_date,
    expiration_date,
    policy_risk_unit_status,
    exposure_unit,
    source_system

from {{ ref('stg_policy_risk_unit') }}
