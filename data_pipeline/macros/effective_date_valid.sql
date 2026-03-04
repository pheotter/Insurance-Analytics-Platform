{% test effective_date_valid(model, column_name, min_date='2010-01-01') %}

select *
from {{ model }}
where {{ column_name }} IS NULL
   OR {{ column_name }} < '{{ min_date }}'
   OR {{ column_name }} > CURRENT_DATE()

{% endtest %}
