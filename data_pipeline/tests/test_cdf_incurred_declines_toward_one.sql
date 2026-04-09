with ordered as (
    select
        *,
        lag(cdf) over (
            partition by state_grp, risk_class_grp, vehicle_segment_grp
            order by development
        ) as prev_cdf
    from {{ ref('int_cdf_incurred') }}
)

select *
from ordered
where prev_cdf is not null
  and cdf > prev_cdf
