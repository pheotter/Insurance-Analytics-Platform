with base as (
    select * from {{ ref('int_ldf_filtered') }}
),

triangle as (
    select * from {{ ref('int_claim_triangle_cumulative') }}
)

select
    b.state_grp,
    b.risk_class_grp,
    b.vehicle_segment_grp,
    b.driver_age_grp,
    b.credit_score_band_grp,
    b.development,

    sum(t2.cumulative_incurred_loss)
    / nullif(sum(t1.cumulative_incurred_loss),0)
    as weighted_ldf

from base b

join triangle t1
    on b.development = t1.development
    and b.state_grp = t1.state_grp
    and b.risk_class_grp = t1.risk_class_grp
    and b.vehicle_segment_grp = t1.vehicle_segment_grp
    and b.driver_age_grp = t1.driver_age_grp
    and b.credit_score_band_grp = t1.credit_score_band_grp
    and b.accident_year = t1.accident_year

join triangle t2
    on t2.development = t1.development + 1
    and t1.state_grp = t2.state_grp
    and t1.risk_class_grp = t2.risk_class_grp
    and t1.vehicle_segment_grp = t2.vehicle_segment_grp
    and t1.driver_age_grp = t2.driver_age_grp
    and t1.credit_score_band_grp = t2.credit_score_band_grp
    and t1.accident_year = t2.accident_year

group by
    b.state_grp,
    b.risk_class_grp,
    b.vehicle_segment_grp,
    b.driver_age_grp,
    b.credit_score_band_grp,
    b.development
