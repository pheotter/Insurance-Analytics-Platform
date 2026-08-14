with earning_segments as (

    select

        transaction_id,
        policy_id,
        coverage_id,
        transaction_type,
        earning_start_date,
        earning_end_date,
        premium_change,
        earning_days

    from {{ ref('int_premium_earning_segments')}}

),

months as (

    select
    
        month_start,
        next_month_start

    from {{ ref('dim_calendar_month') }}

),

expanded as (

    select

        e.transaction_id,
        e.policy_id,
        e.coverage_id,
        e.transaction_type,
        e.premium_change,

        m.month_start as calendar_month,

        greatest(
            e.earning_start_date,
            m.month_start
        ) as earning_start_in_month,

        least(
            e.earning_end_date,
            m.next_month_start
        ) as earning_end_in_month,

        e.earning_days

    from earning_segments e
    join months m
        on m.month_start < e.earning_end_date
       and m.next_month_start > e.earning_start_date

),

monthly as (

    select
        *,

        datediff(
            day,
            earning_start_in_month,
            earning_end_in_month
        ) as earned_days_in_month

    from expanded

)

select

    policy_id,
    coverage_id,
    calendar_month,

    sum(
        premium_change
        * earned_days_in_month
        / nullif(earning_days, 0)
    ) as earned_premium

from monthly
group by policy_id, coverage_id, calendar_month
