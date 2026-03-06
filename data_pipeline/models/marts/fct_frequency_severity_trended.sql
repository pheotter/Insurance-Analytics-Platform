with base as (

    select *
    from {{ ref('fct_frequency_severity') }}

),

trend as (

    select *
    from {{ stg_trend_selection }}
    where segmentation_version = '{{ var("segmentation_version") }}'

),

freq_trend as (

    select *
    from trend
    where trend_type = 'frequency'

),

sev_trend as (

    select *
    from trend
    where trend_type = 'severity'

),

exposure_mid as (

    select
        b.state_grp,
        b.risk_class_grp,
        b.vehicle_segment_grp,
        b.accident_year,
        b.earned_exposure,

        b.frequency,
        b.severity,

        f.annual_trend as trend_freq,
        s.annual_trend as trend_sev,

        DATE_ADD(
            DATE(CONCAT(b.accident_year,'-01-01')),
            INTERVAL 182 DAY
        ) as accident_mid, -- assume policy-term is 1 year

        DATE_ADD(
            DATE_ADD(
                f.effective_from,
                INTERVAL DATEDIFF(f.effective_to, f.effective_from)/2 DAY
            ),
            INTERVAL 182 DAY
        ) as exposure_mid_freq,

        DATE_ADD(
            DATE_ADD(
                s.effective_from,
                INTERVAL DATEDIFF(s.effective_to, s.effective_from)/2 DAY
            ),
            INTERVAL 182 DAY
        ) as exposure_mid_sev

    from base b

    left join freq_trend f
      on b.state_grp = f.state
     and b.risk_class_grp = f.risk_class
     and b.vehicle_segment_grp = f.vehicle_segment

    left join sev_trend s
      on b.state_grp = s.state
     and b.risk_class_grp = s.risk_class
     and b.vehicle_segment_grp = s.vehicle_segment
),

trend_year as (

  select
      *,
      greatest(
          year(exposure_mid_freq) + dayofyear(exposure_mid_freq)/365.25
          - (accident_year + 0.5),
          0
      ) as trend_years_freq,

      greatest(
          year(exposure_mid_sev) + dayofyear(exposure_mid_sev)/365.25
          - (accident_year + 0.5),
          0
      ) as trend_years_sev,
  from exposure_mid

)

select

    state_grp,
    risk_class_grp,
    vehicle_segment_grp,
    accident_year,
    earned_exposure,

    frequency * power(
        1 + coalesce(trend_freq, 0),
        trend_years_freq
    ) as trended_frequency,

    severity * power(
        1 + coalesce(trend_sev, 0),
        trend_years_sev
    ) as trended_severity,

from trend_year
