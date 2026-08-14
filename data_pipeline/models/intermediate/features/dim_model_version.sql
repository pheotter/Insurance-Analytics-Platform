select

    model_version_id,
    product_id,
    line_of_business,
    version_number,
    effective_start_date,
    effective_end_date,
    status

from {{ ref('model_version') }}
