with ldf as (

    select *
    from {{ ref('int_ldf_selected_incurred') }}

)

select
    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    development,
    exp(
        sum(ln(selected_ldf))
        over (
          partition by
            state_grp,
            risk_class_grp,
            vehicle_segment_grp
          order by development desc) -- x1*x2*...xn = exp(sum(lnx1, lnx2,...,lnxn))
    ) as cdf

from ldf
