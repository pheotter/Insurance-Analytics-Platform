select
    claim_id,
    event_date,
    cumulative_incurred_loss,
    calculated_cumulative_incurred,
    calculated_cumulative_incurred - cumulative_incurred_loss as incurred_difference
from {{ ref('int_claim_financial_state_cumulative') }}
where cumulative_incurred_loss is null
   or calculated_cumulative_incurred is null
   or abs(
       calculated_cumulative_incurred
       - cumulative_incurred_loss
   ) > 0.01
