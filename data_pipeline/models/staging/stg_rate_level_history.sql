select

    filing_id,
    effective_date,
    state as state_grp,
    risk_class as risk_class_grp,
    vehicle_segment as vehicle_segment_grp,
    rate_change_pct,
    cumulative_factor

from {{ source('data', 'rate_level_history') }}
