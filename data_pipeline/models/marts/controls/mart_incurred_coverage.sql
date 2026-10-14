with approved as (

    select *
    from {{ ref('int_approved_actuarial_ultimate_selection') }}

),

loss as (

    select distinct
        selection_version_id,
        triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        accident_period
    from approved
    where measure_type = '{{ var("loss_measure", "incurred") }}'

),

claim_count as (

    select distinct
        selection_version_id,
        triangle_grain,
        development_pool_id,
        pool_level,
        line_of_business,
        accident_period
    from approved
    where measure_type = 'reported_count'

),

joined as (

    select
        coalesce(l.selection_version_id, c.selection_version_id)
            as selection_version_id,
        coalesce(l.triangle_grain, c.triangle_grain) as triangle_grain,
        coalesce(l.development_pool_id, c.development_pool_id)
            as development_pool_id,
        coalesce(l.pool_level, c.pool_level) as pool_level,
        coalesce(l.line_of_business, c.line_of_business) as line_of_business,
        coalesce(l.accident_period, c.accident_period) as accident_period,
        case
            when l.accident_period is not null and c.accident_period is not null
                then 'matched'
            when l.accident_period is not null and c.accident_period is null
                then 'missing_reported_count_selection'
            when l.accident_period is null and c.accident_period is not null
                then 'missing_loss_selection'
        end as status
    from loss l
    full outer join claim_count c
      on l.selection_version_id = c.selection_version_id
     and l.triangle_grain = c.triangle_grain
     and l.development_pool_id = c.development_pool_id
     and l.line_of_business = c.line_of_business
     and l.accident_period = c.accident_period

)

select *
from joined
