{% set evaluation_date = var('evaluation_date', '2024-12-31') %}

with claim_base as (

    select *
    from {{ ref('stg_claim') }}

),

claim_policy as (

    select
        c.claim_id,
        c.accident_date,
        c.paid_loss,
        c.case_reserve,
        c.incurred_loss,
        p.state,
        p.risk_class,
        p.vehicle_segment,
        p.driver_age,
        p.credit_score_band
    from claim_base c
    left join {{ ref('stg_policy') }} p
           on c.policy_id = p.policy_id
    where c.accident_date <= to_date('{{ evaluation_date }}')

),

-- generate development years
dev_years as (

    select 0 as development
    union all select 1
    union all select 2
    union all select 3
    union all select 4
    union all select 5

),

claim_with_dev as (

    select
        *,
        floor(
            datediff(day, accident_date, to_date('{{ evaluation_date }}')) / 365.0
        ) as max_dev
    from claim_policy

),

config as (
    select *
    from {{ ref('segmentation_config') }}
    where segmentation_version = 'v1'
),


triangle as (

    select
        {{ segmentation_grouping('state', 'cfg.use_state') }} as state_grp,
        {{ segmentation_grouping('risk_class', 'cfg.use_risk_class') }} as risk_class_grp,
        {{ segmentation_grouping('vehicle_segment', 'cfg.use_vehicle_segment') }} as vehicle_segment_grp,
        {{ segmentation_grouping('driver_age', 'cfg.use_driver_age') }} as driver_age_grp,
        {{ segmentation_grouping('credit_score_band', 'cfg.use_credit_score_band') }} as credit_score_band_grp,
        c.accident_year,
        d.development,
        sum(c.incurred_loss) as incremental_incurred_loss,
        count(distinct c.claim_id) as claim_count
    from claim_with_dev c
    cross join config cfg
    join dev_years d
        on d.development <= c.max_dev
    group by 1,2,3,4,5,6,7

)

select * from triangle
