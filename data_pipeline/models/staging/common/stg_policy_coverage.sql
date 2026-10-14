select

    cast(coverage_id as varchar) as coverage_id,
    cast(policy_id as varchar) as policy_id,
    cast(risk_unit_id as varchar) as risk_unit_id,
    cast(coverage_code as varchar) as coverage_code,
    cast(coverage_family as varchar) as coverage_family,
    cast(effective_date as date) as effective_date,
    cast(expiration_date as date) as expiration_date,
    cast(limit_amount as number(18, 2)) as limit_amount,
    cast(deductible_amount as number(18, 2)) as deductible_amount,
    cast(written_premium as number(18, 2)) as written_premium,
    cast(source_system as varchar) as source_system,
    cast(load_batch_id as varchar) as load_batch_id,
    cast(ingested_at as timestamp_ntz) as ingested_at

from {{ source('data', 'raw_policy_coverage') }}
