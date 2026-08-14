select

    factor_id,
    factor_name,
    entity_level,
    data_type,
    description

from {{ ref('rating_factor') }}
