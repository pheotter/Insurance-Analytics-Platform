select *
from {{ ref('int_policy_exposure') }}
where total_earned_exposure < 0
   or total_earned_premium < 0
