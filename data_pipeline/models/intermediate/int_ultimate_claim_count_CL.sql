with latest_claim_count_per_AY as (

    select

        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        development,
        cumulative_claim_count,
        row_number() over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp,
                  accident_year
            order by development desc
        ) as rn

    from {{ ref('int_claim_triangle_cumulative') }}

),

cdf as (

    select *
    from {{ ref('int_cdf_claim_count') }}

)

select

    t.state_grp,
    t.risk_class_grp,
    t.vehicle_segment_grp,
    t.accident_year,
    t.cumulative_claim_count * coalesce(c.cdf, 1) as ultimate_claim_count

from latest_claim_count_per_AY t
left join cdf c
  on t.development = c.development
 and t.state_grp = c.state_grp
 and t.risk_class_grp = c.risk_class_grp
 and t.vehicle_segment_grp = c.vehicle_segment_grp
where t.rn = 1
