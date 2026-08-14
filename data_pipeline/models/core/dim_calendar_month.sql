-- models/core/dim_calendar_month.sql

{{ config(materialized='view') }}

select distinct
    month_start,
    dateadd(month, 1, month_start) as next_month_start,
    year(month_start) as calendar_year,
    month(month_start) as calendar_month,
    quarter(month_start) as calendar_quarter

from {{ ref('dim_date') }}
