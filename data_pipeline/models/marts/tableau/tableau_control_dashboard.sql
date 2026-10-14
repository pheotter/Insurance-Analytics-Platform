select
    metric_name,
    source_value,
    target_value,
    absolute_difference,
    percentage_difference,
    absolute_tolerance,
    percentage_tolerance,
    control_status

from {{ ref('mart_control_tolerance_by_metric') }}

union all

select
    'selection_loss_and_claim_count_coverage' as metric_name,
    count_if(status = 'matched') as source_value,
    count(*) as target_value,
    count(*) - count_if(status = 'matched') as absolute_difference,
    (count(*) - count_if(status = 'matched')) / nullif(count(*), 0)
        as percentage_difference,
    0 as absolute_tolerance,
    0 as percentage_tolerance,
    case
        when count_if(status <> 'matched') = 0 then 'PASS'
        else 'FAIL'
    end as control_status
from {{ ref('mart_incurred_coverage') }}
