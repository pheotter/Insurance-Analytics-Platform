with ldf as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        driver_age_grp,
        credit_score_band_grp,
        development,
        case
            when override_factor is not null -- assume override_factor is the same for all segmentation
                then override_factor         -- modify this later
            else selected_ldf
        end as final_ldf

    from {{ ref('int_ldf_selected') }}

),

select
    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    driver_age_grp,
    credit_score_band_grp,
    development,
    exp(
        sum(ln(final_ldf))
        over (
          partition by
            state_grp,
            risk_class_grp,
            vehicle_segment_grp,
            driver_age_grp,
            credit_score_band_grp
          order by development desc) -- x1*x2*...xn = exp(sum(lnx1, lnx2,...,lnxn))
    ) as cdf

from ldf
