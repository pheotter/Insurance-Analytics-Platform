with coverage as (

    select *
    from {{ ref('stg_policy_coverage') }}

),

policy as (

    select *
    from {{ ref('stg_policy') }}

),

risk_unit as (

    select *
    from {{ ref('stg_policy_risk_unit') }}

),

joined as (

    select
        c.coverage_id,
        c.policy_id,
        c.risk_unit_id,

        p.product_id,
        p.line_of_business,

        r.risk_unit_type,
        r.exposure_unit,

        c.coverage_code,

        c.effective_date as coverage_effective_date,
        c.expiration_date as scheduled_expiration_date,

        least(
            c.expiration_date,
            coalesce(
                p.cancellation_date,
                c.expiration_date
            )
        ) as actual_expiration_date

    from coverage c
    join policy p
        on c.policy_id = p.policy_id
    join risk_unit r
        on c.risk_unit_id = r.risk_unit_id

)

select * from joined
