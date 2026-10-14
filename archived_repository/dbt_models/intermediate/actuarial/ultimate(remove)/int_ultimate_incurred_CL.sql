with latest_loss_per_AY as (

    select

        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        development,
        cumulative_incurred,
        row_number() over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp,
                  accident_year
            order by development desc
        ) as rn

    from {{ ref('int_claim_triangle_cumulative') }}

),

cdf as (

    select *
    from {{ ref('int_cdf_incurred') }}

)

select

    t.state_grp,
    t.risk_class_grp,
    t.vehicle_segment_grp,
    t.accident_year,
    t.cumulative_incurred * c.cdf as ultimate_loss

from latest_loss_per_AY t
join cdf c
  on t.development = c.development
 and t.state_grp = c.state_grp
 and t.risk_class_grp = c.risk_class_grp
 and t.vehicle_segment_grp = c.vehicle_segment_grp
where t.rn = 1
