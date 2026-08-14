-- models/core/fct_claim.sql

select
    claim_id,
    policy_id,
    risk_unit_id,
    coverage_id,
    loss_date,
    reported_date,
    claim_type,
    cause_code,
    claim_status,
    source_system

from {{ ref('stg_claim') }}
