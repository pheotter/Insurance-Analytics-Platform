with config as (

    select *
    from {{ ref('segmentation_config') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'

),

expected as (

    select
        {{ segmentation_grouping('p.state', 'cfg.use_state') }} as state_grp,
        {{ segmentation_grouping('p.risk_class', 'cfg.use_risk_class') }} as risk_class_grp,
        {{ segmentation_grouping('p.vehicle_segment', 'cfg.use_vehicle_segment') }} as vehicle_segment_grp,
        date_part(year, s.accident_date) as accident_year,
        floor(datediff(month, s.accident_date, s.valuation_date) / 12) as development,
        s.valuation_date,
        sum(s.cumulative_paid) as expected_cumulative_paid,
        sum(s.incurred) as expected_cumulative_incurred,
        count(distinct s.claim_id) as expected_claim_count
    from {{ ref('int_claim_snapshot') }} s
    left join {{ ref('stg_policy') }} p
      on s.policy_id = p.policy_id
    cross join config cfg
    group by 1, 2, 3, 4, 5, 6

),

actual as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        development,
        valuation_date,
        cumulative_paid as actual_cumulative_paid,
        cumulative_incurred as actual_cumulative_incurred,
        cumulative_claim_count as actual_claim_count
    from {{ ref('int_claim_triangle_cumulative') }}

)

select
    coalesce(e.state_grp, a.state_grp) as state_grp,
    coalesce(e.risk_class_grp, a.risk_class_grp) as risk_class_grp,
    coalesce(e.vehicle_segment_grp, a.vehicle_segment_grp) as vehicle_segment_grp,
    coalesce(e.accident_year, a.accident_year) as accident_year,
    coalesce(e.development, a.development) as development,
    coalesce(e.valuation_date, a.valuation_date) as valuation_date,
    e.expected_cumulative_paid,
    a.actual_cumulative_paid,
    e.expected_cumulative_incurred,
    a.actual_cumulative_incurred,
    e.expected_claim_count,
    a.actual_claim_count
from expected e
full outer join actual a
  on e.state_grp = a.state_grp
 and e.risk_class_grp = a.risk_class_grp
 and e.vehicle_segment_grp = a.vehicle_segment_grp
 and e.accident_year = a.accident_year
 and e.development = a.development
 and e.valuation_date = a.valuation_date
where abs(coalesce(e.expected_cumulative_paid, 0) - coalesce(a.actual_cumulative_paid, 0)) > 0.000001
   or abs(coalesce(e.expected_cumulative_incurred, 0) - coalesce(a.actual_cumulative_incurred, 0)) > 0.000001
   or coalesce(e.expected_claim_count, 0) != coalesce(a.actual_claim_count, 0)
