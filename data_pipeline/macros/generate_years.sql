{% macro generate_years(start_model, date_column) %}

with bounds as (

    select
        min({{ date_column }}) as min_date,
        max({{ date_column }}) as max_date
    from {{ ref(start_model) }}

)

select distinct
    d.calendar_year as calendar_year
from {{ ref('dim_date') }} d
join bounds b
on d.date_day between b.min_date and b.max_date

{% endmacro %}
