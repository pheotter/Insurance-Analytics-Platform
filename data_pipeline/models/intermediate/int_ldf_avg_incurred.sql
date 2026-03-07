with link_ratio as (
    select * from {{ ref('int_ldf_raw') }}
),

sel as (
    select *
    from {{ ref('stg_ldf_selection_table_incurred') }}
    where segmentation_version = '{{ var("segmentation_version", "v3") }}'
),

filtered_link_ratio as (

    select l.*
    from link_ratio l
    left join sel s
        on l.development = s.development
        and l.state_grp = s.state_grp
        and l.risk_class_grp = s.risk_class_grp
        and l.vehicle_segment_grp = s.vehicle_segment_grp
    where l.accident_year between s.ay_from and s.ay_to

),

ldf as (

  select
      f.state_grp,
      f.risk_class_grp,
      f.vehicle_segment_grp,
      f.development,

      avg(link_ratio) as avg_ldf

  from filtered_link_ratio f

  group by 1,2,3,4

)

select * from ldf
