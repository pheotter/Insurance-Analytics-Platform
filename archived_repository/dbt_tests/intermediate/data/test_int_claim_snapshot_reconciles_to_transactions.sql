with expected as (

    select
        valuation_date,
        sum(cumulative_paid) as expected_cumulative_paid,
        sum(incurred) as expected_incurred,
        count(distinct claim_id) as expected_claim_count
    from (
        select
            v.valuation_date,
            t.claim_id,
            t.cumulative_paid,
            t.incurred,
            row_number() over (
                partition by v.valuation_date, t.claim_id
                order by t.transaction_date desc
            ) as rn
        from {{ ref('stg_claim') }} t
        join {{ ref('int_valuation_dates') }} v
          on t.transaction_date <= v.valuation_date
    )
    where rn = 1
    group by 1

),

actual as (

    select
        valuation_date,
        sum(cumulative_paid) as actual_cumulative_paid,
        sum(incurred) as actual_incurred,
        count(distinct claim_id) as actual_claim_count
    from {{ ref('int_claim_snapshot') }}
    group by 1

)

select
    coalesce(e.valuation_date, a.valuation_date) as valuation_date,
    e.expected_cumulative_paid,
    a.actual_cumulative_paid,
    e.expected_incurred,
    a.actual_incurred,
    e.expected_claim_count,
    a.actual_claim_count
from expected e
full outer join actual a
  on e.valuation_date = a.valuation_date
where abs(coalesce(e.expected_cumulative_paid, 0) - coalesce(a.actual_cumulative_paid, 0)) > 0.000001
   or abs(coalesce(e.expected_incurred, 0) - coalesce(a.actual_incurred, 0)) > 0.000001
   or coalesce(e.expected_claim_count, 0) != coalesce(a.actual_claim_count, 0)
