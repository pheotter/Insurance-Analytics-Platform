-- models/intermediate/claims/int_valuation_dates.sql

with claim_bounds as (

    select
        date_trunc(
            'month',
            min(loss_date)
        )::date as first_accident_month

    from {{ ref('fct_claim') }}

),

calendar as (

    select
        month_start,
        month_end,

        calendar_year,
        calendar_quarter,
        calendar_month,

        is_quarter_end,
        is_half_year_end,
        is_year_end

    from {{ ref('dim_calendar_month') }}

),

valuation_dates as (

    select
        c.month_end as valuation_date,
        c.month_start as valuation_month,

        c.calendar_year,
        c.calendar_quarter,
        c.calendar_month,

        c.is_quarter_end,
        c.is_half_year_end,
        c.is_year_end

    from calendar c

    cross join claim_bounds b

    where c.month_start >= b.first_accident_month

      and c.month_end <= to_date('{{ var("as_of_date") }}')

)

select *
from valuation_dates
