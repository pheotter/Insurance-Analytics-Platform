select *
from {{ ref('fct_ultimate_claim_count') }}
where method = '{{ var("claim_count_method") }}'
