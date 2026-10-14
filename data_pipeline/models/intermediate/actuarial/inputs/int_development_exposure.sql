with exposure as (

    select
        calendar_month,
        product_id,
        line_of_business,
        coverage_code,
        earned_exposure,
        earned_premium

    from {{ ref('fct_exposure') }}

    where calendar_month <= date_trunc(
        'month',
        to_date('{{ var("as_of_date") }}')
    )

),

pool_mapping as (

    select
        development_pool_id,
        pool_level,
        line_of_business,
        product_id,
        coverage_code

    from {{ ref('development_pool_mapping') }}

),

mapped as (

    select
        m.development_pool_id,
        m.pool_level,
        e.line_of_business,
        e.calendar_month,
        e.earned_exposure,
        e.earned_premium

    from exposure e
    join pool_mapping m
      on e.line_of_business = m.line_of_business
     and e.product_id = m.product_id
     and e.coverage_code = m.coverage_code

),

grain_periods as (

    select
        'monthly' as triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        date_trunc('month', calendar_month)::date as accident_period,
        earned_exposure,
        earned_premium
    from mapped

    union all

    select
        'quarterly' as triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        date_trunc('quarter', calendar_month)::date as accident_period,
        earned_exposure,
        earned_premium
    from mapped

    union all

    select
        'half_year' as triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        date_from_parts(
            year(calendar_month),
            case when month(calendar_month) <= 6 then 1 else 7 end,
            1
        ) as accident_period,
        earned_exposure,
        earned_premium
    from mapped

    union all

    select
        'annual' as triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        date_trunc('year', calendar_month)::date as accident_period,
        earned_exposure,
        earned_premium
    from mapped

)

select
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    accident_period,
    sum(earned_exposure) as earned_exposure,
    sum(earned_premium) as earned_premium,
    sum(earned_premium) as exposure_base

from grain_periods
group by
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    accident_period
