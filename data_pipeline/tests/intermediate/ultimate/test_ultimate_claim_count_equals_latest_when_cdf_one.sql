with latest as (
    select *
    from (
        select
            state_grp,
            risk_class_grp,
            vehicle_segment_grp,
            accident_year,
            development,
            cumulative_claim_count,
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
    l.cumulative_claim_count,
    c.cdf
from {{ ref('int_ultimate_claim_count_CL') }} u
join latest l
  on u.state_grp = l.state_grp
 and u.risk_class_grp = l.risk_class_grp
 and u.vehicle_segment_grp = l.vehicle_segment_grp
 and u.accident_year = l.accident_year
left join {{ ref('int_cdf_claim_count') }} c
  on l.state_grp = c.state_grp
 and l.risk_class_grp = c.risk_class_grp
 and l.vehicle_segment_grp = c.vehicle_segment_grp
 and l.development = c.development
where coalesce(c.cdf, 1) = 1
  and abs(u.ultimate_claim_count - l.cumulative_claim_count) > 0.000001
