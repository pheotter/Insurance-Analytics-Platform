with premium_transaction as (

    select *
    from {{ ref('stg_premium_transaction') }}
    where transaction_type != 'CANCELLATION'

),

coverage as (

    select *
    from {{ ref('int_coverage_active_period') }}

),

months as (

    select *
    from {{ ref('dim_calendar_month') }}

),

earning_segment as (

    select
        t.transaction_id,
        t.policy_id,
        t.coverage_id,

        t.transaction_date as earning_start,

        c.scheduled_expiration_date as scheduled_earning_end,

        c.actual_expiration_date as actual_earning_end,

        t.premium_change

    from premium_transaction t
    join coverage c
        on t.coverage_id = c.coverage_id

),

expanded as (

    select
        e.transaction_id,
        e.coverage_id,
        m.month_start as calendar_month,

        e.premium_change,

        datediff(
            day,
            e.earning_start,
            e.scheduled_earning_end
        ) as scheduled_earning_days,

        datediff(
            day,

            greatest(
                e.earning_start,
                m.month_start
            ),

            least(
                e.actual_earning_end,
                m.next_month_start
            )
        ) as earned_days_in_month

    from earning_segment e
    join months m
        on m.month_start < e.actual_earning_end
       and m.next_month_start > e.earning_start

)

select
    coverage_id,
    calendar_month,

    sum(
        premium_change
        * earned_days_in_month
        / nullif(scheduled_earning_days, 0)
    ) as earned_premium

from expanded
group by
    coverage_id,
    calendar_month
