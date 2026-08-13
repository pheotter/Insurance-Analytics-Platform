select

    coverage_id,
    policy_id,
    risk_unit_id,
    coverage_code,
    coverage_family,
    effective_date,
    expiration_date,
    limit_amount,
    deductible_amount,
    written_premium,
    source_system

from {{ source('data', 'raw_policy_coverage') }}
