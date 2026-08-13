select

    vehicle_id,
    policy_id,
    vehicle_sequence,
    model_year,
    make,
    model,
    vehicle_type,
    garaging_state,
    annual_mileage,
    usage,
    safety_device_flag,
    source_system

from {{ source('data', 'raw_vehicle') }}
