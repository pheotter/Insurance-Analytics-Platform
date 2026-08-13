{{ config(materialized='table') }}

with spine as (
    {{ dbt_utils.date_spine(
        datepart="month",
        start_date="cast('2019-01-01' as date)",
        end_date="cast('2026-01-01' as date)"
    ) }}
)
select
    date_month as month_start,
    dateadd(month, 1, date_month) as next_month_start
from spine
