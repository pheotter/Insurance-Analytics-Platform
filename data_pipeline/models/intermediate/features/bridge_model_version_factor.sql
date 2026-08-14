select

    model_version_id,
    factor_id,
    transformation_id,
    required_flag

from {{ ref('bridge_model_version_factor') }}
