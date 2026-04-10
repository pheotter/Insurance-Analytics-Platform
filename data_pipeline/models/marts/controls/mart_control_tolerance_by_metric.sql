with control_totals as (

    select *
    from {{ ref('mart_control_totals_financial_summary') }}

),

tolerances as (

    select 'written_premium_to_earned_premium_total' as metric_name, 0.01 as absolute_tolerance, 0.000001 as percentage_tolerance
    union all
    select 'written_exposure_to_earned_exposure_total' as metric_name, 0.000001 as absolute_tolerance, 0.000001 as percentage_tolerance
    union all
    select 'latest_cumulative_paid_total' as metric_name, 0.01 as absolute_tolerance, 0.000001 as percentage_tolerance
    union all
    select 'latest_cumulative_incurred_total' as metric_name, 0.01 as absolute_tolerance, 0.000001 as percentage_tolerance
    union all
    select 'latest_claim_count_total' as metric_name, 0.000001 as absolute_tolerance, 0.000001 as percentage_tolerance
),

evaluated as (

    select
        c.metric_name,
        c.source_value,
        c.target_value,
        c.absolute_difference,
        c.percentage_difference,
        t.absolute_tolerance,
        t.percentage_tolerance,
        case
            when abs(c.absolute_difference) <= t.absolute_tolerance
             and abs(coalesce(c.percentage_difference, 0)) <= t.percentage_tolerance
                then 'PASS'
            when abs(c.absolute_difference) <= t.absolute_tolerance * 5
                then 'WARN'
            else 'FAIL'
        end as control_status
    from control_totals c
    left join tolerances t
      on c.metric_name = t.metric_name
)

select *
from evaluated
