select

    cast(claim_id as varchar) as claim_id,
    cast(policy_id as varchar) as policy_id,
    cast(risk_unit_id as varchar) as risk_unit_id,
    cast(coverage_id as varchar) as coverage_id,
    cast(coverage_code as varchar) as coverage_code,
    cast(loss_date as date) as loss_date,
    cast(reported_date as date) as reported_date,
    cast(claim_type as varchar) as claim_type,
    cast(cause_code as varchar) as cause_code,
    cast(claim_status as varchar) as claim_status,
    cast(source_system as varchar) as source_system,
    cast(load_batch_id as varchar) as load_batch_id,
    cast(ingested_at as timestamp_ntz) as ingested_at

from {{ source('data', 'raw_claim') }}
