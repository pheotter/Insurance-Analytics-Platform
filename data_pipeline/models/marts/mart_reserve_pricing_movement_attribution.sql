with base as (

    select
        fs.state_grp,
        fs.risk_class_grp,
        fs.vehicle_segment_grp,
        sum(fs.total_earned_exposure) as total_earned_exposure,
        sum(fs.frequency * fs.severity * fs.total_earned_exposure) / nullif(sum(fs.total_earned_exposure), 0) as base_pure_premium,
        sum(fst.trended_frequency * fst.trended_severity * fst.total_earned_exposure) / nullif(sum(fst.total_earned_exposure), 0) as trended_pure_premium
    from {{ ref('fct_frequency_severity') }} fs
    join {{ ref('fct_frequency_severity_trended') }} fst
      on fs.state_grp = fst.state_grp
     and fs.risk_class_grp = fst.risk_class_grp
     and fs.vehicle_segment_grp = fst.vehicle_segment_grp
     and fs.accident_year = fst.accident_year
    group by 1, 2, 3

),

indicated as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        indicated_premium
    from {{ ref('fct_indicated_premium') }}

),

reserve_impact as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        sum(loss_method_impact) as reserve_loss_method_impact,
        sum(claim_count_method_impact) as reserve_claim_count_method_impact
    from {{ ref('mart_assumption_impact_reconciliation') }}
    group by 1, 2, 3

)

select
    b.state_grp,
    b.risk_class_grp,
    b.vehicle_segment_grp,
    b.total_earned_exposure,
    b.base_pure_premium,
    b.trended_pure_premium,
    i.indicated_premium,
    b.trended_pure_premium - b.base_pure_premium as trend_impact_on_pure_premium,
    i.indicated_premium - b.trended_pure_premium as expense_and_profit_impact,
    r.reserve_loss_method_impact,
    r.reserve_claim_count_method_impact
from base b
left join indicated i
  on b.state_grp = i.state_grp
 and b.risk_class_grp = i.risk_class_grp
 and b.vehicle_segment_grp = i.vehicle_segment_grp
left join reserve_impact r
  on b.state_grp = r.state_grp
 and b.risk_class_grp = r.risk_class_grp
 and b.vehicle_segment_grp = r.vehicle_segment_grp
