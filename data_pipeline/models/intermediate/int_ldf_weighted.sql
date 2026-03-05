with triangle as (
    select * from {{ ref('int_claim_triangle_cumulative') }}
),

ldf as (

  select
      t1.state_grp,
      t1.risk_class_grp,
      t1.vehicle_segment_grp,
      t1.development,

      sum(t2.cumulative_incurred)
      / nullif(sum(t1.cumulative_incurred),0)
      as weighted_ldf

  from triangle t1
  join triangle t2
      on t2.development = t1.development + 1
      and t1.state_grp = t2.state_grp
      and t1.risk_class_grp = t2.risk_class_grp
      and t1.vehicle_segment_grp = t2.vehicle_segment_grp
      and t1.accident_year = t2.accident_year

  group by 1,2,3,4

)

select * from ldf
