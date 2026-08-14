with exposure as (

    select *
    from {{ ref('int_earned_exposure') }}

),

premium as (

    select *
    from {{ ref('int_earned_premium_month') }}

),

policy as (

    select *
    from {{ ref('dim_policy') }}

),

risk_unit as (

    select *
    from {{ ref('dim_risk_unit') }}

),

coverage as (

    select *
    from {{ ref('dim_coverage') }}

)


select

    {{ dbt_utils.generate_surrogate_key([
        'e.risk_unit_id',
        'e.coverage_id',
        'e.calendar_month'
    ]) }} as exposure_id,

    e.policy_id,
    e.risk_unit_id,
    e.coverage_id,
    e.calendar_month,

    p.product_id,
    p.line_of_business,

    r.risk_unit_type,
    r.exposure_unit,

    c.coverage_code,
    c.coverage_family,

    e.earned_exposure,

    coalesce(
        pr.earned_premium,
        0
    ) as earned_premium

from exposure e
left join premium pr
    on e.coverage_id = pr.coverage_id
   and e.calendar_month = pr.calendar_month
join policy p
    on e.policy_id = p.policy_id
join risk_unit r
    on e.risk_unit_id = r.risk_unit_id
join coverage c
    on e.coverage_id = c.coverage_id
