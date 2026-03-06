with ind as (

    select *
    from {{ ref('fct_indicated_premium') }}

),

current as (

    select
        *,
        row_number() over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp
            order by effective_date desc
        ) as rn
    from {{ ref('stg_rate_level_history') }}

),

current_rate as (

    select *
    from current
    where rn = 1

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
