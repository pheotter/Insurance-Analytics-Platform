select *
from {{ ref('fct_ultimate_loss') }}
where method = '{{ var("loss_method") }}'
