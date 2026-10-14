select

    cast(policy_id as varchar) as policy_id,
    cast(policy_number as varchar) as policy_number,
    cast(insured_id as varchar) as insured_id,
    cast(product_id as varchar) as product_id,
    cast(line_of_business as varchar) as line_of_business,
    cast(effective_date as date) as effective_date,
    cast(expiration_date as date) as expiration_date,
    cast(cancellation_date as date) as cancellation_date,
    cast(status as varchar) as policy_status,
    cast(underwriting_tier as varchar) as underwriting_tier,
    cast(primary_state as varchar) as primary_state,
    cast(term_months as number(38, 0)) as term_months,
    cast(source_system as varchar) as source_system,
    cast(load_batch_id as varchar) as load_batch_id,
    cast(ingested_at as timestamp_ntz) as ingested_at
    
from {{ source('data', 'raw_policy') }}
