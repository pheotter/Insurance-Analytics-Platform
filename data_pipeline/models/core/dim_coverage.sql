-- models/core/dim_coverage.sql

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
    source_system

from {{ ref('stg_policy_coverage') }}
