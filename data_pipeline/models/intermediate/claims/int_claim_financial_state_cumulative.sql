-- models/intermediate/claims/int_claim_financial_state_cumulative.sql

with events as (

    select
        claim_id,
        event_date,
        event_type,

        coalesce(paid_loss_change, 0) as paid_loss_change,
        coalesce(case_reserve_change, 0) as case_reserve_change,
        coalesce(paid_expense_change, 0) as paid_expense_change,
        coalesce(case_expense_change, 0) as case_expense_change,
        coalesce(recovery_change, 0) as recovery_change,
        coalesce(incurred_loss_change, 0) as incurred_loss_change

    from {{ ref('int_claim_financial_events') }}

    -- Point-in-time reproducibility:
    -- this valuation run must not use events after the as-of date.
    where event_date <= to_date('{{ var("as_of_date") }}')

),

daily_events as (

    select
        claim_id,
        event_date,

        max(
            case
                when event_type = 'REPORTED_ANCHOR'
                then 1
                else 0
            end
        ) as has_reported_anchor,

        sum(
            case
                when event_type = 'FINANCIAL_TRANSACTION'
                then 1
                else 0
            end
        ) as financial_transaction_count,

        sum(paid_loss_change) as paid_loss_change,
        sum(case_reserve_change) as case_reserve_change,
        sum(paid_expense_change) as paid_expense_change,
        sum(case_expense_change) as case_expense_change,
        sum(recovery_change) as recovery_change,
        sum(incurred_loss_change) as incurred_loss_change

    from events
    group by claim_id, event_date

),

cumulative as (

    select
        claim_id,
        event_date,

        has_reported_anchor,
        financial_transaction_count,

        paid_loss_change,
        case_reserve_change,
        paid_expense_change,
        case_expense_change,
        recovery_change,
        incurred_loss_change,

        sum(financial_transaction_count) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_financial_transaction_count,

        sum(paid_loss_change) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_paid_loss,

        sum(case_reserve_change) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_case_reserve,

        sum(paid_expense_change) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_paid_expense,

        sum(case_expense_change) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_case_expense,

        sum(recovery_change) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_recovery,

        sum(incurred_loss_change) over (
            partition by claim_id
            order by event_date
            rows between unbounded preceding and current row
        ) as cumulative_incurred_loss

    from daily_events

)

select
    claim_id,
    event_date,

    has_reported_anchor,
    financial_transaction_count,
    cumulative_financial_transaction_count,

    paid_loss_change,
    case_reserve_change,
    paid_expense_change,
    case_expense_change,
    recovery_change,
    incurred_loss_change,

    cumulative_paid_loss,
    cumulative_case_reserve,
    cumulative_paid_expense,
    cumulative_case_expense,
    cumulative_recovery,
    cumulative_incurred_loss,

    cumulative_paid_loss
        + cumulative_case_reserve
        + cumulative_paid_expense
        + cumulative_case_expense
        - cumulative_recovery
        as calculated_cumulative_incurred,

    case
        when cumulative_financial_transaction_count > 0
        then true
        else false
    end as has_financial_activity

from cumulative
