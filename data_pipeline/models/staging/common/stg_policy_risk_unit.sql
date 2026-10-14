select

    cast(risk_unit_id as varchar) as risk_unit_id,
    cast(policy_id as varchar) as policy_id,
    cast(risk_unit_type as varchar) as risk_unit_type,
    cast(source_risk_unit_id as varchar) as source_risk_unit_id,
    cast(effective_date as date) as effective_date,
    cast(expiration_date as date) as expiration_date,
    cast(status as varchar) as policy_risk_unit_status,
    cast(exposure_unit as varchar) as exposure_unit,
    cast(source_system as varchar) as source_system,
    cast(load_batch_id as varchar) as load_batch_id,
    cast(ingested_at as timestamp_ntz) as ingested_at

from {{ source('data', 'raw_policy_risk_unit') }}
