with triangle as (

    select *
    from {{ ref('int_claim_triangle_cumulative') }}

),

paired_development as (

    select
        t1.state_grp,
        t1.risk_class_grp,
        t1.vehicle_segment_grp,
        t1.accident_year,
        t1.development
    from triangle t1
    join triangle t2
      on t1.state_grp = t2.state_grp
     and t1.risk_class_grp = t2.risk_class_grp
     and t1.vehicle_segment_grp = t2.vehicle_segment_grp
     and t1.accident_year = t2.accident_year
     and t2.development = t1.development + 1

),

available_pairs as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        development,
        count(*) as ay_count
    from paired_development
    group by 1, 2, 3, 4

),

model_output as (

    select *
    from {{ ref('int_ldf_last3_weighted') }}

)

select
    m.*
from model_output m
left join available_pairs a
  on m.state_grp = a.state_grp
 and m.risk_class_grp = a.risk_class_grp
 and m.vehicle_segment_grp = a.vehicle_segment_grp
 and m.development = a.development
where coalesce(a.ay_count, 0) < 3
  and (
      abs(m.last3_ldf_paid - 1) > 0.000001
      or abs(m.last3_ldf_incurred - 1) > 0.000001
      or abs(m.last3_ldf_cnt - 1) > 0.000001
  )
