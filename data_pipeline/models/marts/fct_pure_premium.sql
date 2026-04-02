select

    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    accident_year,
    total_exposure,

    trended_frequency,
    trended_severity,

    trended_frequency * trended_severity
        as pure_premium

from {{ ref('fct_frequency_severity_trended') }}
