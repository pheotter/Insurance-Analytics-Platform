with latest_snapshot_date as (

    select max(valuation_date) as valuation_date
    from {{ ref('int_claim_valuation_snapshot') }}

),

claim_transactions as (

    select
        sum(paid_loss_change) as paid_loss,
        sum(paid_loss_change + paid_expense_change) as paid_and_expense,
        sum(incurred_loss_change) as incurred_loss,
        count(distinct claim_id) as reported_claim_count
    from {{ ref('fct_claim_transaction') }}
    where transaction_date <= to_date('{{ var("as_of_date") }}')

),

latest_snapshot as (

    select
        sum(cumulative_paid_loss) as paid_loss,
        sum(cumulative_paid_loss + cumulative_paid_expense) as paid_and_expense,
        sum(cumulative_incurred_loss) as incurred_loss,
        count(distinct claim_id) as reported_claim_count
    from {{ ref('int_claim_valuation_snapshot') }}
    where valuation_date = (select valuation_date from latest_snapshot_date)

),

pooled_triangle as (

    select
        sum(cumulative_paid_loss) as paid_loss,
        sum(cumulative_paid_loss + cumulative_paid_expense) as paid_and_expense,
        sum(cumulative_incurred_loss) as incurred_loss,
        sum(cumulative_reported_claim_count) as reported_claim_count
    from {{ ref('int_loss_triangle_pooled') }}
    where triangle_grain = '{{ var("triangle_grain", "annual") }}'
      and valuation_date = (select valuation_date from latest_snapshot_date)

),

exposure_fact as (

    select
        sum(earned_exposure) as earned_exposure,
        sum(earned_premium) as earned_premium
    from {{ ref('fct_exposure') }}
    where calendar_month <= date_trunc('month', to_date('{{ var("as_of_date") }}'))

),

development_exposure as (

    select
        sum(earned_exposure) as earned_exposure,
        sum(earned_premium) as earned_premium
    from {{ ref('int_development_exposure') }}
    where triangle_grain = '{{ var("triangle_grain", "annual") }}'

),

metrics as (

    select
        'claim_transactions_to_latest_snapshot_paid_loss' as metric_name,
        c.paid_loss as source_value,
        s.paid_loss as target_value
    from claim_transactions c
    cross join latest_snapshot s

    union all

    select
        'claim_transactions_to_latest_snapshot_incurred_loss' as metric_name,
        c.incurred_loss as source_value,
        s.incurred_loss as target_value
    from claim_transactions c
    cross join latest_snapshot s

    union all

    select
        'latest_snapshot_to_pooled_triangle_incurred_loss' as metric_name,
        s.incurred_loss as source_value,
        t.incurred_loss as target_value
    from latest_snapshot s
    cross join pooled_triangle t

    union all

    select
        'latest_snapshot_to_pooled_triangle_claim_count' as metric_name,
        s.reported_claim_count as source_value,
        t.reported_claim_count as target_value
    from latest_snapshot s
    cross join pooled_triangle t

    union all

    select
        'fct_exposure_to_development_exposure_earned_exposure' as metric_name,
        f.earned_exposure as source_value,
        d.earned_exposure as target_value
    from exposure_fact f
    cross join development_exposure d

    union all

    select
        'fct_exposure_to_development_exposure_earned_premium' as metric_name,
        f.earned_premium as source_value,
        d.earned_premium as target_value
    from exposure_fact f
    cross join development_exposure d

)

select
    metric_name,
    source_value,
    target_value,
    target_value - source_value as absolute_difference,
    (target_value - source_value) / nullif(abs(source_value), 0)
        as percentage_difference
from metrics
