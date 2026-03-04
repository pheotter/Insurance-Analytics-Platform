with historical as (
    select * from {{ ref('int_ultimate_loss') }}
),

actual as (
    select
        state,
        risk_class,
        vehicle_segment,
        driver_age,
        credit_score_band,
        accident_year,
        max(cumulative_incurred_loss) as actual_ultimate
    from {{ ref('int_claim_triangle_cumulative') }}
    group by 1,2,3,4,5,6
)

select
    h.*,
    a.actual_ultimate,

    (h.ultimate_loss - a.actual_ultimate)
        / nullif(a.actual_ultimate,0) as pct_error

from historical h
left join actual a
    on h.state = a.state
    and h.risk_class = a.risk_class
    and h.vehicle_segment = a.vehicle_segment
    and h.driver_age = a.driver_age
    and h.credit_score_band = a.credit_score_band
    and h.accident_year = a.accident_year
