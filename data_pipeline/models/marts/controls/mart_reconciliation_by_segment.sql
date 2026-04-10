with latest_snapshot_date as (

    select max(valuation_date) as valuation_date
    from {{ ref('int_claim_snapshot') }}

),

config as (
    select *
    from {{ ref('segmentation_config') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'
),

source_claims as (

    select
        {{ segmentation_grouping('p.state', 'cfg.use_state') }} as state_grp,
        {{ segmentation_grouping('p.risk_class', 'cfg.use_risk_class') }} as risk_class_grp,
        {{ segmentation_grouping('p.vehicle_segment', 'cfg.use_vehicle_segment') }} as vehicle_segment_grp,
        sum(s.cumulative_paid) as source_cumulative_paid,
        sum(s.incurred) as source_cumulative_incurred,
        count(distinct s.claim_id) as source_claim_count
    from {{ ref('int_claim_snapshot') }} s
    left join {{ ref('stg_policy') }} p
      on s.policy_id = p.policy_id
    cross join config cfg
    where s.valuation_date = (select valuation_date from latest_snapshot_date)
    group by 1, 2, 3

),

target_claims as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        sum(cumulative_paid) as target_cumulative_paid,
        sum(cumulative_incurred) as target_cumulative_incurred,
        sum(cumulative_claim_count) as target_claim_count
    from {{ ref('int_claim_triangle_cumulative') }}
    where valuation_date = (select valuation_date from latest_snapshot_date)
    group by 1, 2, 3

),

exposure as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        sum(total_earned_exposure) as total_earned_exposure,
        sum(total_earned_premium) as total_earned_premium
    from {{ ref('int_policy_exposure') }}
    group by 1, 2, 3
)

select
    coalesce(s.state_grp, t.state_grp, e.state_grp) as state_grp,
    coalesce(s.risk_class_grp, t.risk_class_grp, e.risk_class_grp) as risk_class_grp,
    coalesce(s.vehicle_segment_grp, t.vehicle_segment_grp, e.vehicle_segment_grp) as vehicle_segment_grp,
    s.source_cumulative_paid,
    t.target_cumulative_paid,
    t.target_cumulative_paid - s.source_cumulative_paid as paid_difference,
    s.source_cumulative_incurred,
    t.target_cumulative_incurred,
    t.target_cumulative_incurred - s.source_cumulative_incurred as incurred_difference,
    s.source_claim_count,
    t.target_claim_count,
    t.target_claim_count - s.source_claim_count as claim_count_difference,
    e.total_earned_exposure,
    e.total_earned_premium
from source_claims s
full outer join target_claims t
  on s.state_grp = t.state_grp
 and s.risk_class_grp = t.risk_class_grp
 and s.vehicle_segment_grp = t.vehicle_segment_grp
full outer join exposure e
  on coalesce(s.state_grp, t.state_grp) = e.state_grp
 and coalesce(s.risk_class_grp, t.risk_class_grp) = e.risk_class_grp
 and coalesce(s.vehicle_segment_grp, t.vehicle_segment_grp) = e.vehicle_segment_grp
