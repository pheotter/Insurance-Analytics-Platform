with ind as (

    select *
    from {{ ref('fct_indicated_premium') }}

),

config as (

    select *
    from {{ ref('segmentation_config') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'

),

detailed_current as (

    select
        *,
        row_number() over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp
            order by effective_date desc
        ) as rn
    from {{ ref('stg_rate_level_history') }}

),

current_rate as (

    select
        {{ segmentation_grouping('state_grp', 'cfg.use_state') }} as state_grp,
        {{ segmentation_grouping('risk_class_grp', 'cfg.use_risk_class') }} as risk_class_grp,
        {{ segmentation_grouping('vehicle_segment_grp', 'cfg.use_vehicle_segment') }} as vehicle_segment_grp,
        avg(cumulative_factor) as cumulative_factor
    from detailed_current
    cross join config cfg
    where rn = 1
    group by 1, 2, 3

)

select

    i.state_grp,
    i.risk_class_grp,
    i.vehicle_segment_grp,
    i.indicated_premium,
    c.cumulative_factor,

    i.indicated_premium / c.cumulative_factor - 1
        as indicated_rate_change

from ind i
join current_rate c
  on i.state_grp = c.state_grp
 and i.risk_class_grp = c.risk_class_grp
 and i.vehicle_segment_grp = c.vehicle_segment_grp
