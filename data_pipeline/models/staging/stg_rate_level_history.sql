select

    filing_id,
    effective_date,
    state,
    risk_class,
    vehicle_segment,
    rate_change_pct,
    cumulative_factor

from {{ source('data', 'rate_level_history') }}
