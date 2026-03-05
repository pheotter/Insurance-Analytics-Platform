with cum as (

    select *
    from {{ ref('int_claim_triangle_cumulative') }}

),

incremental as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        development,

        cumulative_paid
        - lag(cumulative_paid) over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp, accident_year
            order by development
        ) as incremental_paid,

        cumulative_incurred
        - lag(cumulative_incurred) over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp, accident_year
            order by development
        ) as incremental_incurred,

        cumulative_claim_count
        - lag(cumulative_claim_count) over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp, accident_year
            order by development
        ) as incremental_claim_count

    from cum

)

select *
from incremental
