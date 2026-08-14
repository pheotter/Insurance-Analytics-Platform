with premium_transactions as (

    select

        transaction_id,
        policy_id,
        coverage_id,
        transaction_type,
        transaction_date as earning_start_date,
        premium_change

    from {{ ref('stg_premium_transaction') }}

),

coverage as (

    select

        coverage_id,
        effective_date as coverage_effective_date,
        expiration_date as scheduled_expiration_date

    from {{ ref('stg_policy_coverage') }}

),

earning_segments as (

    select
        t.transaction_id,
        t.policy_id,
        t.coverage_id,
        t.transaction_type,
        t.earning_start_date,
        c.scheduled_expiration_date as earning_end_date,
        t.premium_change,

        datediff(
            day,
            t.earning_start_date,
            c.scheduled_expiration_date
        ) as earning_days

    from premium_transactions t
    join coverage c
        on t.coverage_id = c.coverage_id

)

select *
from earning_segments
