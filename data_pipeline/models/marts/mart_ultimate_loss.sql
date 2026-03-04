with latest_loss_per_AY as (

    select

        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        driver_age_grp,
        credit_score_band_grp,
        accident_year,
        development,
        cumulative_incurred_loss,
        row_number() over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp,
                  driver_age_grp, credit_score_band_grp, accident_year
            order by development desc
        ) as rn

    from {{ ref('int_claim_triangle_cumulative') }}

),

cdf as (

    select *
    from {{ ref('int_cdf') }}

)

select

    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    driver_age_grp,
    credit_score_band_grp,
    t.accident_year,
    t.cumulative_incurred_loss * c.cdf as ultimate_loss

from latest_loss_per_AY t
join cdf c
  on t.development = c.development
 and t.state_grp = c.state_grp
 and t.risk_class_grp = c.risk_class_grp
 and t.vehicle_segment_grp = c.vehicle_segment_grp
 and t.driver_age_grp = c.driver_age_grp
 and t.credit_score_band_grp = c.credit_score_band_grp
where t.rn = 1
