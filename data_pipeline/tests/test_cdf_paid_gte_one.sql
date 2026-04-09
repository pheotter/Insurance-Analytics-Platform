select *
from {{ ref('int_cdf_paid') }}
where cdf < 1
