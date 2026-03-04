{% macro segmentation_grouping(column_name, flag_column) %}
    case
        when {{ flag_column }} = 1 then {{ column_name }}
        else 'ALL'
    end
{% endmacro %}
