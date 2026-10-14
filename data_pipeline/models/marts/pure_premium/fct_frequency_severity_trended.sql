with base as (

    select *
    from {{ ref('fct_actuarial_frequency_severity') }}

),

trend_global as (

    select
        trend_type,
        avg(annual_trend) as annual_trend,
        min(effective_from) as effective_from,
        max(effective_to) as effective_to
    from {{ ref('stg_trend_selection') }}
    group by trend_type

),

frequency_trend as (

    select *
    from trend_global
    where trend_type = 'frequency'

),

severity_trend as (

    select *
    from trend_global
    where trend_type = 'severity'

),

with_midpoints as (

    select
        b.*,

        case b.triangle_grain
            when 'monthly' then dateadd(day, 15, b.accident_period)
            when 'quarterly' then dateadd(day, 45, b.accident_period)
            when 'half_year' then dateadd(day, 91, b.accident_period)
            when 'annual' then dateadd(day, 182, b.accident_period)
            else dateadd(day, 182, b.accident_period)
        end as accident_midpoint,

        dateadd(
            day,
            datediff(day, f.effective_from, f.effective_to) / 2,
            f.effective_from
        ) as frequency_trend_midpoint,

        dateadd(
            day,
            datediff(day, s.effective_from, s.effective_to) / 2,
            s.effective_from
        ) as severity_trend_midpoint,

        f.annual_trend as frequency_annual_trend,
        s.annual_trend as severity_annual_trend

    from base b
    left join frequency_trend f
        on 1 = 1
    left join severity_trend s
        on 1 = 1

),

trend_years as (

    select
        *,
        greatest(
            datediff(day, accident_midpoint, frequency_trend_midpoint) / 365.25,
            0
        ) as frequency_trend_years,
        greatest(
            datediff(day, accident_midpoint, severity_trend_midpoint) / 365.25,
            0
        ) as severity_trend_years
    from with_midpoints

)

select
    selection_version_id,
    triangle_grain,
    development_pool_id,
    pool_level,
    line_of_business,
    accident_period,
    earned_exposure,
    earned_premium,
    ultimate_claim_count,
    ultimate_loss,
    claim_count_method,
    loss_method,
    frequency,
    severity,
    pure_premium as untrended_pure_premium,
    frequency_annual_trend,
    severity_annual_trend,
    frequency_trend_years,
    severity_trend_years,
    frequency * power(
        1 + coalesce(frequency_annual_trend, 0),
        coalesce(frequency_trend_years, 0)
    ) as trended_frequency,
    severity * power(
        1 + coalesce(severity_annual_trend, 0),
        coalesce(severity_trend_years, 0)
    ) as trended_severity

from trend_years
