with latest_snapshot_date as (

    select max(valuation_date) as valuation_date
    from {{ ref('int_claim_snapshot') }}

),

source_policy as (

    select
        sum(written_premium) as total_written_premium,
        sum(term_months / 12.0) as total_written_exposure
    from {{ ref('stg_policy') }}

),

target_policy as (

    select
        sum(total_earned_premium) as total_earned_premium,
        sum(total_earned_exposure) as total_earned_exposure
    from {{ ref('int_policy_exposure') }}

),

source_claims as (

    select
        sum(cumulative_paid) as latest_cumulative_paid,
        sum(incurred) as latest_cumulative_incurred,
        count(distinct claim_id) as latest_claim_count
    from {{ ref('int_claim_snapshot') }}
    where valuation_date = (select valuation_date from latest_snapshot_date)

),

target_claims as (

    select
        sum(cumulative_paid) as latest_cumulative_paid,
        sum(cumulative_incurred) as latest_cumulative_incurred,
        sum(cumulative_claim_count) as latest_claim_count
    from {{ ref('int_claim_triangle_cumulative') }}
    where valuation_date = (select valuation_date from latest_snapshot_date)

),

metrics as (

    select
        'written_premium_to_earned_premium_total' as metric_name,
        p.total_written_premium as source_value,
        t.total_earned_premium as target_value
    from source_policy p
    cross join target_policy t

    union all

    select
        'written_exposure_to_earned_exposure_total' as metric_name,
        p.total_written_exposure as source_value,
        t.total_earned_exposure as target_value
    from source_policy p
    cross join target_policy t

    union all

    select
        'latest_cumulative_paid_total' as metric_name,
        s.latest_cumulative_paid as source_value,
        t.latest_cumulative_paid as target_value
    from source_claims s
    cross join target_claims t

    union all

    select
        'latest_cumulative_incurred_total' as metric_name,
        s.latest_cumulative_incurred as source_value,
        t.latest_cumulative_incurred as target_value
    from source_claims s
    cross join target_claims t

    union all

    select
        'latest_claim_count_total' as metric_name,
        s.latest_claim_count as source_value,
        t.latest_claim_count as target_value
    from source_claims s
    cross join target_claims t
)

select
    metric_name,
    source_value,
    target_value,
    target_value - source_value as absolute_difference,
    (target_value - source_value) / nullif(abs(source_value), 0) as percentage_difference
from metrics
