with bounds as (

    select
        to_date('2015-12-31') as start_valuation_date,
        coalesce(last_day(max(transaction_date), 'year'), to_date('2015-12-31')) as end_valuation_date
    from {{ ref('stg_claim') }}

),

valuation_dates as (

    select
        dateadd(year, seq4(), start_valuation_date) as valuation_date,
        end_valuation_date
    from bounds,
         table(generator(rowcount => 50))

)

select valuation_date
from valuation_dates
where valuation_date <= end_valuation_date
order by valuation_date
