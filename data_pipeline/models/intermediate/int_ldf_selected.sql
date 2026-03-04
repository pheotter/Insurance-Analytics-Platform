with base as (
    select * from {{ ref('int_ldf_filtered') }}
),

weighted as (
    select * from {{ ref('int_ldf_weighted') }}
)

select
    b.state_grp,
    b.risk_class_grp,
    b.vehicle_segment_grp,
    b.driver_age_grp,
    b.credit_score_band_grp,
    b.development,

    case
        when b.method = 'avg'
            then avg(b.link_ratio)

        when b.method = 'weighted'
            then max(w.weighted_ldf)

        when b.method = 'last3'
            then avg(
                case
                    when b.accident_year >=
                         max(b.accident_year) over (
                             partition by b.state_grp,
                                          b.risk_class_grp,
                                          b.vehicle_segment_grp,
                                          b.driver_age_grp,
                                          b.credit_score_band_grp,
                                          b.development
                         ) - 2
                    then b.link_ratio
                end
            )
    end as selected_ldf,

    max(b.override_factor) as override_factor

from base b
left join weighted w
    on b.state_grp = w.state_grp
    and b.risk_class_grp = w.risk_class_grp
    and b.vehicle_segment_grp = w.vehicle_segment_grp
    and b.driver_age_grp = w.driver_age_grp
    and b.credit_score_band_grp = w.credit_score_band_grp
    and b.development = w.development

group by
    b.state_grp,
    b.risk_class_grp,
    b.vehicle_segment_grp,
    b.driver_age_grp,
    b.credit_score_band_grp,
    b.development,
    b.method
