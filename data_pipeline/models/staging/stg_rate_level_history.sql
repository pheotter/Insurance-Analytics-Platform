select

    filing_id,
    effective_date,
    state,
    risk_class,
    cumulative_factor

from {{ source('data', 'dim_rate_level_history') }}
