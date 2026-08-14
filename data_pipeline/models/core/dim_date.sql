{{ config(materialized='table') }}

with date_spine as (

  {{
      dbt_utils.date_spine(
          datepart="day",
          start_date="cast('" ~ var('calendar_start_date') ~ "' as date)",
          end_date="cast('" ~ var('calendar_end_date') ~ "' as date)"
      )
  }}

)

select
    date_day, -- column name generate by date_spine

    year(date_day) as calendar_year,
    quarter(date_day) as calendar_quarter,
    month(date_day) as calendar_month,
    day(date_day) as calendar_day, -- 這個月的第幾天

    date_trunc('month', date_day) as month_start, -- first day of the month, easier to group
    date_trunc('quarter', date_day) as quarter_start,
    date_trunc('year', date_day) as year_start, -- first day of the year, easier to group

    -- Calendar half-year indicator
    case
        when month(date_day) <= 6 then 1
        else 2
    end as half_year

from date_spine
