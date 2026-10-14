with selected as (

    select *
    from {{ ref('int_approved_actuarial_ultimate_selection') }}

),

loss as (

    select *
    from selected
    where measure_type = '{{ var("loss_measure", "incurred") }}'

),

claim_count as (

    select *
    from selected
    where measure_type = 'reported_count'

),

exposure as (

    select *
    from {{ ref('int_development_exposure') }}

)

select
    l.selection_version_id,
    l.triangle_grain,
    l.development_pool_id,
    l.pool_level,
    l.line_of_business,
    l.accident_period,
    e.earned_exposure,
    e.earned_premium,
    c.selected_ultimate_value as ultimate_claim_count,
    l.selected_ultimate_value as ultimate_loss,
    c.selected_ultimate_method as claim_count_method,
    l.selected_ultimate_method as loss_method,
    c.selected_ultimate_value / nullif(e.earned_exposure, 0) as frequency,
    l.selected_ultimate_value / nullif(c.selected_ultimate_value, 0) as severity,
    l.selected_ultimate_value / nullif(e.earned_exposure, 0) as pure_premium

from loss l
inner join claim_count c
    on l.selection_version_id = c.selection_version_id
   and l.triangle_grain = c.triangle_grain
   and l.development_pool_id = c.development_pool_id
   and l.line_of_business = c.line_of_business
   and l.accident_period = c.accident_period
left join exposure e
    on l.triangle_grain = e.triangle_grain
   and l.development_pool_id = e.development_pool_id
   and l.line_of_business = e.line_of_business
   and l.accident_period = e.accident_period
