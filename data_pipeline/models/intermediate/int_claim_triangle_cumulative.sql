with snapshot as (

    select *
    from {{ ref('int_claim_snapshot') }}

),

policy as (

    select *
    from {{ ref('stg_policy') }}

),

joined as (

    select
        s.valuation_date,
        date_part(year, s.accident_date) as accident_year,

        floor(
            datediff(month, s.accident_date, s.valuation_date) / 12
        ) as development,

        p.state,
        p.risk_class,
        p.vehicle_segment,

        s.claim_id,
        s.cumulative_paid,
        s.incurred
    from snapshot s
    left join policy p
        on s.policy_id = p.policy_id
),

config as (
    select *
    from {{ ref('segmentation_config') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'
),


triangle as (

    select
        {{ segmentation_grouping('state', 'cfg.use_state') }} as state_grp,
        {{ segmentation_grouping('risk_class', 'cfg.use_risk_class') }} as risk_class_grp,
        {{ segmentation_grouping('vehicle_segment', 'cfg.use_vehicle_segment') }} as vehicle_segment_grp,
        j.accident_year,
        j.development,
        j.valuation_date,
        sum(j.cumulative_paid) as cumulative_paid,
        sum(j.incurred)        as cumulative_incurred,
        count(distinct j.claim_id) as cumulative_claim_count
    from joined j
    cross join config cfg
    group by 1,2,3,4,5,6

)

select * from triangle
