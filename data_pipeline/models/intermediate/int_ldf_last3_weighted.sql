with base as (

    select *
    from {{ ref('int_claim_triangle_cumulative') }}

),

max_ay as (

    select
        state_grp, risk_class_grp, vehicle_segment_grp,
        max(accident_year) as max_ay
    from base
    group by 1,2,3
),

filtered as (

    select b.*
    from base b
    join max_ay m
      on b.state_grp = m.state_grp
     and b.risk_class_grp = m.risk_class_grp
     and b.vehicle_segment_grp = m.vehicle_segment_grp
     and b.accident_year >= m.max_ay - 2

),

ldf as (

    select
        t1.state_grp,
        t1.risk_class_grp,
        t1.vehicle_segment_grp,
        t1.development,

        sum(t2.cumulative_incurred)
        / nullif(sum(t1.cumulative_incurred),0) as last3_ldf,

        sum(t2.cumulative_claim_count)
        / nullif(sum(t1.cumulative_claim_count),0) as last3_ldf_cnt


    from filtered t1
    join filtered t2
        on t1.state_grp = t2.state_grp
       and t1.risk_class_grp = t2.risk_class_grp
       and t1.vehicle_segment_grp = t2.vehicle_segment_grp
       and t1.accident_year = t2.accident_year
       and t2.development = t1.development + 1

    group by 1,2,3,4
)

select *
from ldf
