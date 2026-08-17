with expected as (

    select
        v.valuation_date,
        count(distinct c.claim_id) as expected_claim_count

    from {{ ref('int_valuation_dates') }} v

    join {{ ref('fct_claim') }} c
      on c.reported_date <= v.valuation_date

    group by v.valuation_date

),

actual as (

    select
        valuation_date,
        count(distinct claim_id) as actual_claim_count

    from {{ ref('int_claim_valuation_snapshot') }}

    group by valuation_date

)

select
    e.valuation_date,
    e.expected_claim_count,
    a.actual_claim_count

from expected e

left join actual a
    on e.valuation_date = a.valuation_date

where e.expected_claim_count != coalesce(a.actual_claim_count, 0)
