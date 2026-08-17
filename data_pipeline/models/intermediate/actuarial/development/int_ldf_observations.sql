with triangle as (

    select
        triangle_grain,

        product_id,
        line_of_business,
        coverage_code,

        accident_period,
        development_age_months,

        cumulative_reported_claim_count,
        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss

    from {{ ref('int_loss_triangle') }}

),

with_step as (

    select
        *,

        case
            when triangle_grain = 'monthly' then 1
            when triangle_grain = 'quarterly' then 3
            when triangle_grain = 'half_year' then 6
            when triangle_grain = 'annual' then 12
        end as development_step_months

    from triangle

),

development_pairs as (

    select
        a.triangle_grain,

        a.product_id,
        a.line_of_business,
        a.coverage_code,

        a.accident_period,

        a.development_age_months
            as development_age_from,

        b.development_age_months
            as development_age_to,


        -- Paid
        a.cumulative_paid_loss
            as paid_loss_from,

        b.cumulative_paid_loss
            as paid_loss_to,

        case
            when a.cumulative_paid_loss > 0
            then b.cumulative_paid_loss
                 / a.cumulative_paid_loss
        end as paid_link_ratio,

        -- Paid + Paid expense
        a.cumulative_paid_loss + a.cumulative_paid_expense
            as paid_and_expense_loss_from,

        b.cumulative_paid_loss + b.cumulative_paid_expense
            as paid_and_expense_loss_to,

        case
            when a.cumulative_paid_loss + a.cumulative_paid_expense > 0
            then (b.cumulative_paid_loss  + b.cumulative_paid_expense)
                 / (a.cumulative_paid_loss + a.cumulative_paid_expense)
        end as paid_and_expense_link_ratio,


        -- Incurred
        a.cumulative_incurred_loss
            as incurred_loss_from,

        b.cumulative_incurred_loss
            as incurred_loss_to,

        case
            when a.cumulative_incurred_loss > 0
            then b.cumulative_incurred_loss
                 / a.cumulative_incurred_loss
        end as incurred_link_ratio,


        -- Reported claim count
        a.cumulative_reported_claim_count
            as reported_claim_count_from,

        b.cumulative_reported_claim_count
            as reported_claim_count_to,

        case
            when a.cumulative_reported_claim_count > 0
            then b.cumulative_reported_claim_count
                 / a.cumulative_reported_claim_count
        end as reported_count_link_ratio

    from with_step a

    join with_step b
        on a.triangle_grain = b.triangle_grain
       and a.product_id = b.product_id
       and a.line_of_business = b.line_of_business
       and a.coverage_code = b.coverage_code
       and a.accident_period = b.accident_period

       and b.development_age_months
           = a.development_age_months
             + a.development_step_months

)

select *
from development_pairs
