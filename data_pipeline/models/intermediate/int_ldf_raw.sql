with triangle as (
    select * from {{ ref('int_claim_triangle_cumulative') }}
)

select
    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    accident_year,
    development,

    lead(cumulative_incurred) over (
        partition by state_grp, risk_class_grp, vehicle_segment_grp,
                     accident_year
        order by development
    ) / nullif(cumulative_incurred,0) -- if cumulative_incurred_loss = 0 then turn it to null
    as link_ratio                     -- if lead() is null, then link_ratio will be null

from triangle
