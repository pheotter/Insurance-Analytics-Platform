with base as (

    select *
    from {{ ref('fct_pure_premium') }}

),

expense as (

    select *
    from {{ ref('stg_expense_assumption') }}

),

agg as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,

        sum(trended_frequency* trended_severity * earned_exposure)
        / sum(earned_exposure) as pure_premium

    from base
    group by 1,2,3

)


select

    a.state_grp,
    a.risk_class_grp,
    a.vehicle_segment_grp,

    (a.pure_premium * (1 + e.ulae_ratio)
    + e.fixed_expense_per_exposure)
    /
    (1 - e.variable_expense_ratio - e.profit_ratio)
    as indicated_premium

from agg a
join expense e
  on a.state_grp = e.state_grp
 and a.risk_class_grp = e.risk_class_grp
 and a.vehicle_segment_grp = e.vehicle_segment_grp
