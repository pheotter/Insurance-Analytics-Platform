with claim_ay as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        driver_age_grp,
        credit_score_band_grp,
        accident_year,
        sum(claim_count) as total_claim_count
    from {{ ref('int_claim_triangle_incremental') }}
    group by 1,2,3,4,5,6

),

exposure_ay as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        driver_age_grp,
        credit_score_band_grp,
        calendar_year as accident_year,
        sum(total_exposure) as total_exposure
    from {{ ref('int_policy_exposure') }}
    group by 1,2,3,4,5,6

)

select
    c.state_grp,
    c.risk_class_grp,
    c.accident_year,

    c.total_claim_count / nullif(e.total_exposure,0) as frequency

from claim_ay c
join exposure_ay e
  on ...
