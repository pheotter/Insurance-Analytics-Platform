select

    assignment_id,
    policy_id,
    driver_id,
    vehicle_id,
    assignment_type,
    effective_date,
    expiration_date,
    source_system

from {{ source('data', 'raw_driver_vehicle_assignment') }}
