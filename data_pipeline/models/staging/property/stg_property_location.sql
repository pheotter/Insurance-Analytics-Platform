select

    location_id,
    policy_id,
    location_sequence,
    state,
    zip_code,
    occupancy,
    construction_type,
    year_built,
    protection_class,
    total_insured_value,
    source_system

from {{ source('data', 'raw_property_location') }}
