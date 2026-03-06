with policy_base as (

    select *
    from {{ ref('stg_policy') }}

),

policy_actual as (
    select
        *,
        least(expiration_date, coalesce(cancellation_date, expiration_date)) as actual_end_date,
        term_months / 12.0 as term_factor
    from policy_base
),

cy as (

    {{ generate_years('stg_policy', 'effective_date') }}

),

policy_year as (

    select
        p.policy_id,
        p.state,
        p.risk_class,
        p.vehicle_segment,
        p.term_factor,
        p.written_premium,
        c.calendar_year,

        greatest(
            p.effective_date,
            to_date(c.calendar_year || '-01-01')
        ) as earn_start,

        least(
            p.actual_end_date,
            to_date(c.calendar_year || '-12-31')
        ) as earn_end,

        datediff(day, p.effective_date, p.actual_end_date) as total_days

    from policy_actual p
    cross join cy c
    where
        p.effective_date <= to_date(c.calendar_year || '-12-31')
        and p.actual_end_date >= to_date(c.calendar_year || '-01-01')
),

calculate_fraction as (

    select

        policy_id,
        state,
        risk_class,
        vehicle_segment,
        term_factor,
        written_premium,
        calendar_year,
        COALESCE(
            greatest(datediff(day, earn_start, earn_end), 0) / NULLIF(total_days, 0)::float,
            0
        ) as year_fraction

    from policy_year

),

policy_earned as (

    select

        policy_id,
        state,
        risk_class,
        vehicle_segment,
        calendar_year,

        term_factor * year_fraction as earned_exposure,
        written_premium * year_fraction as earned_premium

    from calculate_fraction

),

config as (
    select *
    from {{ ref('segmentation_config') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'
)

select

    {{ segmentation_grouping('state', 'cfg.use_state') }} as state_grp,
    {{ segmentation_grouping('risk_class', 'cfg.use_risk_class') }} as risk_class_grp,
    {{ segmentation_grouping('vehicle_segment', 'cfg.use_vehicle_segment') }} as vehicle_segment_grp,

    calendar_year,
    sum(earned_exposure) as total_exposure,
    sum(earned_premium) as total_earned_premium

from policy_earned
cross join config cfg

group by 1,2,3,4
