with valuation as (

    select *
    from {{ ref('dim_valuation_dates') }}

),

transactions as (

    select *
    from {{ ref('stg_claim') }}

),

expanded as (

    select
        v.valuation_date,
        t.claim_id,
        t.policy_id,
        t.accident_date,
        t.transaction_date,
        t.cumulative_paid,
        t.case_reserve,
        t.incurred
    from transactions t
    join valuation v
      on t.transaction_date <= v.valuation_date

),

latest_per_claim as (

    select *
    from (
        select *,
            row_number() over (
                partition by claim_id, valuation_date
                order by transaction_date desc
            ) as rn
        from expanded
    )
    where rn = 1

)

select *
from latest_per_claim
