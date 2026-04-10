with link_ratio as (
    select * from {{ ref('int_ldf_raw') }}
),

ldf as (

  select
      f.state_grp,
      f.risk_class_grp,
      f.vehicle_segment_grp,
      f.development,

      coalesce(avg(link_ratio_paid), 1) as avg_ldf_paid,
      coalesce(avg(link_ratio_incurred), 1) as avg_ldf_incurred,
      coalesce(avg(link_ratio_cnt), 1) as avg_ldf_cnt

  from link_ratio f

  group by 1,2,3,4

)

select * from ldf
