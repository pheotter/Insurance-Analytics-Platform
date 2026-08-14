-- models/intermediate/features/int_property_exposure_attributes.sql

with exposures as (

    select
        exposure_id,
        policy_id,
        risk_unit_id,
        coverage_id,
        calendar_month

    from {{ ref('fct_exposure') }}

    where line_of_business = 'commercial_property'

),

policies as (

    select
        policy_id,
        effective_date as policy_effective_date

    from {{ ref('dim_policy') }}

),

risk_units as (

    select
        risk_unit_id,
        source_risk_unit_id

    from {{ ref('dim_risk_unit') }}

    where risk_unit_type = 'property_location'

),

locations as (

    select
        location_id,
        state,
        occupancy,
        construction_type,
        year_built,
        protection_class,
        total_insured_value

    from {{ ref('stg_property_location') }}

),

base as (

    select
        e.exposure_id,
        e.policy_id,
        e.risk_unit_id,
        e.coverage_id,
        e.calendar_month,

        p.policy_effective_date,

        l.state,
        l.occupancy,
        l.construction_type,
        l.year_built,
        l.protection_class,
        l.total_insured_value

    from exposures e

    inner join policies p
        on e.policy_id = p.policy_id

    inner join risk_units r
        on e.risk_unit_id = r.risk_unit_id

    inner join locations l
        on r.source_risk_unit_id = l.location_id

),

derived as (

    select
        *,

        greatest(
            year(policy_effective_date) - year_built,
            0
        ) as building_age

    from base

),

attributes as (

    select
        exposure_id,
        'RF_STATE' as factor_id,
        null::number as value_numeric,
        state::varchar as value_string
    from derived

    union all

    select
        exposure_id,
        'RF_OCCUPANCY',
        null::number,
        occupancy::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_CONSTRUCTION_TYPE',
        null::number,
        construction_type::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_BUILDING_AGE',
        building_age::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_PROTECTION_CLASS',
        protection_class::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_TIV',
        total_insured_value::number,
        null::varchar
    from derived

)

select
    exposure_id,
    factor_id,
    value_numeric,
    value_string

from attributes
