-- models/intermediate/claims/int_claim_development.sql

with snapshots as (

    select *
    from {{ ref('int_claim_valuation_snapshot') }}

),

development as (

    select
        *,

        -- =====================================================
        -- Accident periods
        -- =====================================================

        date_trunc('month', loss_date)::date
            as accident_month,

        date_trunc('quarter', loss_date)::date
            as accident_quarter,

        case
            when month(loss_date) <= 6
                then date_from_parts(year(loss_date), 1, 1)
            else date_from_parts(year(loss_date), 7, 1)
        end as accident_half_year,

        date_trunc('year', loss_date)::date
            as accident_year,

        -- =====================================================
        -- Development ages
        --
        -- +1 gives:
        -- same accident month      -> 1 month
        -- same accident quarter Q1 -> 3 months at Mar 31
        -- same accident year       -> 12 months at Dec 31
        -- =====================================================

        datediff(
            month,
            date_trunc('month', loss_date),
            valuation_month
        ) + 1 as development_age_monthly,

        datediff(
            month,
            date_trunc('quarter', loss_date),
            valuation_month
        ) + 1 as development_age_quarterly,

        datediff(
            month,
            case
                when month(loss_date) <= 6
                    then date_from_parts(year(loss_date), 1, 1)
                else date_from_parts(year(loss_date), 7, 1)
            end,
            valuation_month
        ) + 1 as development_age_half_year,

        datediff(
            month,
            date_trunc('year', loss_date),
            valuation_month
        ) + 1 as development_age_annual

    from snapshots

)

select *
from development
