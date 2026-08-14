-- models/features/fct_exposure_attribute.sql

with auto_attributes as (

    select
        exposure_id,
        factor_id,
        value_numeric,
        value_string

    from {{ ref('int_auto_exposure_attributes') }}

),

property_attributes as (

    select
        exposure_id,
        factor_id,
        value_numeric,
        value_string

    from {{ ref('int_property_exposure_attributes') }}

),

combined as (

    select * from auto_attributes

    union all

    select * from property_attributes

)

select

    exposure_id,
    factor_id,
    value_numeric,
    value_string

from combined
