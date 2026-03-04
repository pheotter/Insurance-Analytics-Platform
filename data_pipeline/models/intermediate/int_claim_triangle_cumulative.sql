select

    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    driver_age_grp,
    credit_score_band_grp,
    accident_year,
    development,

    sum(incremental_incurred_loss)
        over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp,
                         driver_age_grp, credit_score_band_grp, accident_year
            order by development
        ) as cumulative_incurred_loss

from {{ ref('int_claim_triangle_incremental') }}
