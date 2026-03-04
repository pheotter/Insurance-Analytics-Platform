{{ config(materialized='table') }}

with date_spine as (

    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="to_date('2010-01-01')",
            end_date="dateadd(year, 5, current_date)"
        )
    }}

)

select
    date_day, -- column name generate by date_spine

    year(date_day) as calendar_year,
    month(date_day) as calendar_month,
    day(date_day) as calendar_day, -- 這個月的第幾天

    date_trunc('month', date_day) as month_start, -- first day of the month, easier to group
    date_trunc('year', date_day) as year_start, -- first day of the year, easier to group

    case when month(date_day) <= 6 then 1 else 2 end as half_year -- rate filing to seperate first half of year and

from date_spine
