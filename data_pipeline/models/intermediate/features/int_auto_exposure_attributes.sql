-- models/intermediate/features/int_auto_exposure_attributes.sql

with exposures as (

    select
        exposure_id,
        policy_id,
        risk_unit_id,
        coverage_id,
        calendar_month

    from {{ ref('fct_exposure') }}

    where line_of_business = 'personal_auto'

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

    where risk_unit_type = 'vehicle'

),

vehicles as (

    select
        vehicle_id,
        garaging_state,
        model_year,
        vehicle_type,
        annual_mileage,
        usage

    from {{ ref('stg_vehicle') }}

),

primary_drivers as (

    select
        policy_id,
        vehicle_id,
        driver_id

    from {{ ref('stg_driver_vehicle_assignment') }}

    where assignment_type = 'PRIMARY'

),

drivers as (

    select
        driver_id,
        date_of_birth,
        prior_accidents,
        prior_violations,
        credit_tier

    from {{ ref('stg_driver') }}

),

base as (

    select
        e.exposure_id,
        e.policy_id,
        e.risk_unit_id,
        e.coverage_id,
        e.calendar_month,

        p.policy_effective_date,

        v.garaging_state,
        v.model_year,
        v.vehicle_type,
        v.annual_mileage,
        v.usage,

        d.date_of_birth,
        d.prior_accidents,
        d.prior_violations,
        d.credit_tier

    from exposures e

    inner join policies p
        on e.policy_id = p.policy_id

    inner join risk_units r
        on e.risk_unit_id = r.risk_unit_id

    inner join vehicles v
        on r.source_risk_unit_id = v.vehicle_id

    inner join primary_drivers pd
        on v.vehicle_id = pd.vehicle_id
       and e.policy_id = pd.policy_id

    inner join drivers d
        on pd.driver_id = d.driver_id

),

derived as (

    select
        *,

        year(policy_effective_date)
        - year(date_of_birth)
        - case
            when to_char(policy_effective_date, 'MMDD')
                 < to_char(date_of_birth, 'MMDD')
            then 1
            else 0
          end as driver_age,

        greatest(
            year(policy_effective_date) - model_year,
            0
        ) as vehicle_age

    from base

),

attributes as (

    select
        exposure_id,
        'RF_STATE' as factor_id,
        null::number as value_numeric,
        garaging_state::varchar as value_string
    from derived

    union all

    select
        exposure_id,
        'RF_DRIVER_AGE',
        driver_age::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_PRIOR_ACCIDENTS',
        prior_accidents::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_PRIOR_VIOLATIONS',
        prior_violations::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_CREDIT_TIER',
        null::number,
        credit_tier::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_VEHICLE_AGE',
        vehicle_age::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_VEHICLE_TYPE',
        null::number,
        vehicle_type::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_ANNUAL_MILEAGE',
        annual_mileage::number,
        null::varchar
    from derived

    union all

    select
        exposure_id,
        'RF_USAGE',
        null::number,
        usage::varchar
    from derived

)

select
    exposure_id,
    factor_id,
    value_numeric,
    value_string

from attributes
