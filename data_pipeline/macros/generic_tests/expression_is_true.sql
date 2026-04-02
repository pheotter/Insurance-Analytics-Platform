{% test expression_is_true(model, expression, column_name=None) %}
  {{ return(adapter.dispatch('test_expression_is_true', 'data_pipeline')(model, expression, column_name)) }}
{% endtest %}

{% macro default__test_expression_is_true(model, expression, column_name) %}

select
    1
from {{ model }}
{% if column_name is none %}
where not({{ expression }})
{%- else %}
where not({{ column_name }} {{ expression }})
{%- endif %}

{% endmacro %}
