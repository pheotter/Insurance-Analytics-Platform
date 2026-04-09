with latest as (
    select *
    from (
        select
            state_grp,
            risk_class_grp,
            vehicle_segment_grp,
            accident_year,
            cumulative_paid,
            row_number() over (
                partition by state_grp, risk_class_grp, vehicle_segment_grp, accident_year
                order by development desc
            ) as rn
        from {{ ref('int_claim_triangle_cumulative') }}
    )
    where rn = 1
)

select
    u.*,
    l.cumulative_paid
from {{ ref('int_ultimate_incurred_CL') }} u
join latest l
  on u.state_grp = l.state_grp
 and u.risk_class_grp = l.risk_class_grp
 and u.vehicle_segment_grp = l.vehicle_segment_grp
 and u.accident_year = l.accident_year
where u.ultimate_loss < l.cumulative_paid
