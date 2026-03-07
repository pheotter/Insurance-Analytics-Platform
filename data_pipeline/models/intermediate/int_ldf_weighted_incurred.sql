with triangle as (
    select * from {{ ref('int_claim_triangle_cumulative') }}
),

sel as (
    select *
    from {{ ref('stg_ldf_selection_table_incurred') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'
),

filtered_triangle as (

    select t.*
    from triangle t
    left join sel s
        on t.development = s.development
        and t.state_grp = s.state_grp
        and t.risk_class_grp = s.risk_class_grp
        and t.vehicle_segment_grp = s.vehicle_segment_grp
    where t.accident_year between s.ay_from and s.ay_to

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

  from filtered_triangle t1
  join filtered_triangle t2
      on t2.development = t1.development + 1
      and t1.state_grp = t2.state_grp
      and t1.risk_class_grp = t2.risk_class_grp
      and t1.vehicle_segment_grp = t2.vehicle_segment_grp
      and t1.accident_year = t2.accident_year

  group by 1,2,3,4

)

select * from ldf
