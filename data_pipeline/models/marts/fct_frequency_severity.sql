select

    c.state_grp,
    c.risk_class_grp,
    c.vehicle_segment_grp,
    c.accident_year,
    c.method as claim_count_method,
    l.method as loss_method,
    e.total_earned_exposure,
    c.ultimate_claim_count / nullif(e.total_earned_exposure,0) as frequency,
    l.ultimate_loss / nullif(c.ultimate_claim_count,0)  as severity

from {{ ref('fct_selected_ultimate_claim_count') }} c
join {{ ref('fct_selected_ultimate_loss') }} l
  on c.state_grp = l.state_grp
 and c.risk_class_grp = l.risk_class_grp
 and c.vehicle_segment_grp = l.vehicle_segment_grp
 and c.accident_year = l.accident_year

left join {{ ref('int_policy_exposure') }} e
on c.state_grp = e.state_grp
and c.risk_class_grp = e.risk_class_grp
and c.vehicle_segment_grp = e.vehicle_segment_grp
and c.accident_year = e.calendar_year
