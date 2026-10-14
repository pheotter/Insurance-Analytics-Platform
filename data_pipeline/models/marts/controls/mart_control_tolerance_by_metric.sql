with control_totals as (

    select *
    from {{ ref('mart_control_totals_financial_summary') }}

),

tolerances as (

    select
        'claim_transactions_to_latest_snapshot_paid_loss' as metric_name,
        0.01 as absolute_tolerance,
        0.000001 as percentage_tolerance
    union all
    select
        'claim_transactions_to_latest_snapshot_incurred_loss',
        0.01,
        0.000001
    union all
    select
        'latest_snapshot_to_pooled_triangle_incurred_loss',
        0.01,
        0.000001
    union all
    select
        'latest_snapshot_to_pooled_triangle_claim_count',
        0.000001,
        0.000001
    union all
    select
        'fct_exposure_to_development_exposure_earned_exposure',
        0.000001,
        0.000001
    union all
    select
        'fct_exposure_to_development_exposure_earned_premium',
        0.01,
        0.000001

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
