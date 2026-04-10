with base as (

    select *
    from {{ ref('int_claim_triangle_cumulative') }}

),

segment_developments as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        development
    from base
    group by 1, 2, 3, 4
),

paired_development as (

    select
        t1.state_grp,
        t1.risk_class_grp,
        t1.vehicle_segment_grp,
        t1.accident_year,
        t1.development,
        t1.cumulative_paid,
        t2.cumulative_paid as next_cumulative_paid,
        t1.cumulative_incurred,
        t2.cumulative_incurred as next_cumulative_incurred,
        t1.cumulative_claim_count,
        t2.cumulative_claim_count as next_cumulative_claim_count
    from base t1
    join base t2
      on t1.state_grp = t2.state_grp
     and t1.risk_class_grp = t2.risk_class_grp
     and t1.vehicle_segment_grp = t2.vehicle_segment_grp
     and t1.accident_year = t2.accident_year
     and t2.development = t1.development + 1

),

ranked_pairs as (

    select
        *,
        row_number() over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp, development
            order by accident_year desc
        ) as ay_rank
    from paired_development

),

selected_last3 as (

    select *
    from ranked_pairs
    where ay_rank <= 3

),

aggregated_ldf as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        development,
        count(*) as ay_count,

        sum(next_cumulative_paid)
        / nullif(sum(cumulative_paid), 0) as last3_ldf_paid,

        sum(next_cumulative_incurred)
        / nullif(sum(cumulative_incurred), 0) as last3_ldf_incurred,

        sum(next_cumulative_claim_count)
        / nullif(sum(cumulative_claim_count), 0) as last3_ldf_cnt

    from selected_last3
    group by 1, 2, 3, 4
)

select
    d.state_grp,
    d.risk_class_grp,
    d.vehicle_segment_grp,
    d.development,
    case
        when a.ay_count = 3 then coalesce(a.last3_ldf_paid, 1)
        else 1
    end as last3_ldf_paid,
    case
        when a.ay_count = 3 then coalesce(a.last3_ldf_incurred, 1)
        else 1
    end as last3_ldf_incurred,
    case
        when a.ay_count = 3 then coalesce(a.last3_ldf_cnt, 1)
        else 1
    end as last3_ldf_cnt
from segment_developments d
left join aggregated_ldf a
  on d.state_grp = a.state_grp
 and d.risk_class_grp = a.risk_class_grp
 and d.vehicle_segment_grp = a.vehicle_segment_grp
 and d.development = a.development
