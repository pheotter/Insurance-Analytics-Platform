with latest_snapshot_date as (

    select max(valuation_date) as valuation_date
    from {{ ref('int_claim_valuation_snapshot') }}

),

pool_mapping as (

    select distinct
        development_pool_id,
        pool_level,
        line_of_business,
        product_id,
        coverage_code
    from {{ ref('development_pool_mapping') }}

),

source_claims as (

    select
        m.development_pool_id,
        m.pool_level,
        s.line_of_business,
        sum(s.cumulative_paid_loss) as source_cumulative_paid_loss,
        sum(s.cumulative_paid_loss + s.cumulative_paid_expense)
            as source_cumulative_paid_and_expense,
        sum(s.cumulative_incurred_loss) as source_cumulative_incurred_loss,
        count(distinct s.claim_id) as source_reported_claim_count
    from {{ ref('int_claim_valuation_snapshot') }} s
    join pool_mapping m
      on s.line_of_business = m.line_of_business
     and s.product_id = m.product_id
     and s.coverage_code = m.coverage_code
    where s.valuation_date = (select valuation_date from latest_snapshot_date)
    group by
        m.development_pool_id,
        m.pool_level,
        s.line_of_business

),

target_triangle as (

    select
        development_pool_id,
        pool_level,
        line_of_business,
        sum(cumulative_paid_loss) as target_cumulative_paid_loss,
        sum(cumulative_paid_loss + cumulative_paid_expense)
            as target_cumulative_paid_and_expense,
        sum(cumulative_incurred_loss) as target_cumulative_incurred_loss,
        sum(cumulative_reported_claim_count) as target_reported_claim_count
    from {{ ref('int_loss_triangle_pooled') }}
    where triangle_grain = '{{ var("triangle_grain", "annual") }}'
      and valuation_date = (select valuation_date from latest_snapshot_date)
    group by
        development_pool_id,
        pool_level,
        line_of_business

),

exposure as (

    select
        development_pool_id,
        pool_level,
        line_of_business,
        sum(earned_exposure) as earned_exposure,
        sum(earned_premium) as earned_premium
    from {{ ref('int_development_exposure') }}
    where triangle_grain = '{{ var("triangle_grain", "annual") }}'
    group by
        development_pool_id,
        pool_level,
        line_of_business

)

select
    coalesce(s.development_pool_id, t.development_pool_id, e.development_pool_id)
        as development_pool_id,
    coalesce(s.pool_level, t.pool_level, e.pool_level) as pool_level,
    coalesce(s.line_of_business, t.line_of_business, e.line_of_business)
        as line_of_business,
    s.source_cumulative_paid_loss,
    t.target_cumulative_paid_loss,
    t.target_cumulative_paid_loss - s.source_cumulative_paid_loss
        as paid_loss_difference,
    s.source_cumulative_paid_and_expense,
    t.target_cumulative_paid_and_expense,
    t.target_cumulative_paid_and_expense - s.source_cumulative_paid_and_expense
        as paid_and_expense_difference,
    s.source_cumulative_incurred_loss,
    t.target_cumulative_incurred_loss,
    t.target_cumulative_incurred_loss - s.source_cumulative_incurred_loss
        as incurred_loss_difference,
    s.source_reported_claim_count,
    t.target_reported_claim_count,
    t.target_reported_claim_count - s.source_reported_claim_count
        as reported_claim_count_difference,
    e.earned_exposure,
    e.earned_premium
from source_claims s
full outer join target_triangle t
  on s.development_pool_id = t.development_pool_id
 and s.line_of_business = t.line_of_business
full outer join exposure e
  on coalesce(s.development_pool_id, t.development_pool_id)
        = e.development_pool_id
 and coalesce(s.line_of_business, t.line_of_business)
        = e.line_of_business
