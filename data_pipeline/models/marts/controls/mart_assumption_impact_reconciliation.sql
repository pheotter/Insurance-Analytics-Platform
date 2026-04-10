with selected_loss as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        method as selected_loss_method,
        ultimate_loss as selected_ultimate_loss
    from {{ ref('fct_selected_ultimate_loss') }}

),

selected_claim_count as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        method as selected_claim_count_method,
        ultimate_claim_count as selected_ultimate_claim_count
    from {{ ref('fct_selected_ultimate_claim_count') }}

),

chain_ladder_loss as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        ultimate_loss as chain_ladder_ultimate_loss
    from {{ ref('fct_ultimate_loss') }}
    where method = 'Chain_ladder'

),

chain_ladder_claim_count as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        ultimate_claim_count as chain_ladder_ultimate_claim_count
    from {{ ref('fct_ultimate_claim_count') }}
    where method = 'Chain_ladder'

),

trend_frequency as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        annual_trend as selected_frequency_trend
    from {{ ref('stg_trend_selection') }}
    where trend_type = 'frequency'

),

trend_severity as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        annual_trend as selected_severity_trend
    from {{ ref('stg_trend_selection') }}
    where trend_type = 'severity'

)

select
    coalesce(sl.state_grp, sc.state_grp) as state_grp,
    coalesce(sl.risk_class_grp, sc.risk_class_grp) as risk_class_grp,
    coalesce(sl.vehicle_segment_grp, sc.vehicle_segment_grp) as vehicle_segment_grp,
    coalesce(sl.accident_year, sc.accident_year) as accident_year,
    sl.selected_loss_method,
    sc.selected_claim_count_method,
    sl.selected_ultimate_loss,
    cll.chain_ladder_ultimate_loss,
    sl.selected_ultimate_loss - cll.chain_ladder_ultimate_loss as loss_method_impact,
    sc.selected_ultimate_claim_count,
    clc.chain_ladder_ultimate_claim_count,
    sc.selected_ultimate_claim_count - clc.chain_ladder_ultimate_claim_count as claim_count_method_impact,
    tf.selected_frequency_trend,
    ts.selected_severity_trend
from selected_loss sl
full outer join selected_claim_count sc
  on sl.state_grp = sc.state_grp
 and sl.risk_class_grp = sc.risk_class_grp
 and sl.vehicle_segment_grp = sc.vehicle_segment_grp
 and sl.accident_year = sc.accident_year
left join chain_ladder_loss cll
  on coalesce(sl.state_grp, sc.state_grp) = cll.state_grp
 and coalesce(sl.risk_class_grp, sc.risk_class_grp) = cll.risk_class_grp
 and coalesce(sl.vehicle_segment_grp, sc.vehicle_segment_grp) = cll.vehicle_segment_grp
 and coalesce(sl.accident_year, sc.accident_year) = cll.accident_year
left join chain_ladder_claim_count clc
  on coalesce(sl.state_grp, sc.state_grp) = clc.state_grp
 and coalesce(sl.risk_class_grp, sc.risk_class_grp) = clc.risk_class_grp
 and coalesce(sl.vehicle_segment_grp, sc.vehicle_segment_grp) = clc.vehicle_segment_grp
 and coalesce(sl.accident_year, sc.accident_year) = clc.accident_year
left join trend_frequency tf
  on coalesce(sl.state_grp, sc.state_grp) = tf.state_grp
 and coalesce(sl.risk_class_grp, sc.risk_class_grp) = tf.risk_class_grp
 and coalesce(sl.vehicle_segment_grp, sc.vehicle_segment_grp) = tf.vehicle_segment_grp
left join trend_severity ts
  on coalesce(sl.state_grp, sc.state_grp) = ts.state_grp
 and coalesce(sl.risk_class_grp, sc.risk_class_grp) = ts.risk_class_grp
 and coalesce(sl.vehicle_segment_grp, sc.vehicle_segment_grp) = ts.vehicle_segment_grp
