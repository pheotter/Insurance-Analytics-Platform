-- models/core/dim_calendar_month.sql

{{ config(materialized='view') }}

select distinct
    month_start,
    last_day(month_start) as month_end
    dateadd(month, 1, month_start) as next_month_start,
    
    year(month_start) as calendar_year,
    month(month_start) as calendar_month,
    quarter(month_start) as calendar_quarter

    case
        when month(month_start) in (3, 6, 9, 12)
        then true
        else false
    end as is_quarter_end,

    case
        when month(month_start) in (6, 12)
        then true
        else false
    end as is_half_year_end,

    case
        when month(month_start) = 12
        then true
        else false
    end as is_year_end

from {{ ref('dim_date') }}
