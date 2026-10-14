select *
from {{ ref('int_cdf_claim_count') }}
where cdf < 1
