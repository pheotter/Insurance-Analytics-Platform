with reported_anchor as (

    select
        claim_id,
        reported_date as event_date,

        0::number as paid_loss_change,
        0::number as case_reserve_change,
        0::number as paid_expense_change,
        0::number as case_expense_change,
        0::number as recovery_change,
        0::number as incurred_loss_change,

        'REPORTED_ANCHOR' as event_type

    from {{ ref('fct_claim') }}

),

financial_transactions as (

    select
        claim_id,
        transaction_date as event_date,

        paid_loss_change,
        case_reserve_change,
        paid_expense_change,
        case_expense_change,
        recovery_change,
        incurred_loss_change,

        'FINANCIAL_TRANSACTION' as event_type

    from {{ ref('fct_claim_transaction') }}

),

all_events as (

    select * from reported_anchor

    union all

    select * from financial_transactions

)

select *
from all_events
