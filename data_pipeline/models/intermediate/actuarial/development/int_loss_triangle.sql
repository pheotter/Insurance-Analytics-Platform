-- models/actuarial/development/int_loss_triangle.sql

with development as (

    select
        valuation_date,
        valuation_month,

        is_quarter_end,
        is_half_year_end,
        is_year_end,

        claim_id,

        product_id,
        line_of_business,
        coverage_code,

        accident_month,
        accident_quarter,
        accident_half_year,
        accident_year,

        development_age_monthly,
        development_age_quarterly,
        development_age_half_year,
        development_age_annual,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss

    from {{ ref('int_claim_development') }}

),


-- ============================================================
-- MONTHLY
--
-- Grain:
-- product × coverage × accident month × development month
-- ============================================================

monthly_base as (

    select
        product_id,
        line_of_business,
        coverage_code,

        accident_month as accident_period,

        development_age_monthly
            as development_age_months,

        count(distinct claim_id)
            as cumulative_reported_claim_count,

        sum(cumulative_paid_loss)
            as cumulative_paid_loss,

        sum(cumulative_case_reserve)
            as cumulative_case_reserve,

        sum(cumulative_paid_expense)
            as cumulative_paid_expense,

        sum(cumulative_case_expense)
            as cumulative_case_expense,

        sum(cumulative_recovery)
            as cumulative_recovery,

        sum(cumulative_incurred_loss)
            as cumulative_incurred_loss

    from development

    where development_age_monthly > 0

    group by
        product_id,
        line_of_business,
        coverage_code,
        accident_month,
        development_age_monthly

),

monthly_triangle as (

    select
        'monthly' as triangle_grain,

        product_id,
        line_of_business,
        coverage_code,

        accident_period,
        development_age_months,

        last_day(
            dateadd(
                month,
                development_age_months - 1,
                accident_period
            )
        ) as valuation_date,

        cumulative_reported_claim_count,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss

    from monthly_base

),


-- ============================================================
-- QUARTERLY
--
-- Development ages:
-- 3, 6, 9, 12, ...
-- ============================================================

quarterly_base as (

    select
        product_id,
        line_of_business,
        coverage_code,

        accident_quarter as accident_period,

        development_age_quarterly
            as development_age_months,

        count(distinct claim_id)
            as cumulative_reported_claim_count,

        sum(cumulative_paid_loss)
            as cumulative_paid_loss,

        sum(cumulative_case_reserve)
            as cumulative_case_reserve,

        sum(cumulative_paid_expense)
            as cumulative_paid_expense,

        sum(cumulative_case_expense)
            as cumulative_case_expense,

        sum(cumulative_recovery)
            as cumulative_recovery,

        sum(cumulative_incurred_loss)
            as cumulative_incurred_loss

    from development

    where is_quarter_end = true
      and development_age_quarterly > 0

    group by
        product_id,
        line_of_business,
        coverage_code,
        accident_quarter,
        development_age_quarterly

),

quarterly_triangle as (

    select
        'quarterly' as triangle_grain,

        product_id,
        line_of_business,
        coverage_code,

        accident_period,
        development_age_months,

        last_day(
            dateadd(
                month,
                development_age_months - 1,
                accident_period
            )
        ) as valuation_date,

        cumulative_reported_claim_count,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss

    from quarterly_base

),


-- ============================================================
-- HALF-YEAR
--
-- Development ages:
-- 6, 12, 18, 24, ...
-- ============================================================

half_year_base as (

    select
        product_id,
        line_of_business,
        coverage_code,

        accident_half_year as accident_period,

        development_age_half_year
            as development_age_months,

        count(distinct claim_id)
            as cumulative_reported_claim_count,

        sum(cumulative_paid_loss)
            as cumulative_paid_loss,

        sum(cumulative_case_reserve)
            as cumulative_case_reserve,

        sum(cumulative_paid_expense)
            as cumulative_paid_expense,

        sum(cumulative_case_expense)
            as cumulative_case_expense,

        sum(cumulative_recovery)
            as cumulative_recovery,

        sum(cumulative_incurred_loss)
            as cumulative_incurred_loss

    from development

    where is_half_year_end = true
      and development_age_half_year > 0

    group by
        product_id,
        line_of_business,
        coverage_code,
        accident_half_year,
        development_age_half_year

),

half_year_triangle as (

    select
        'half_year' as triangle_grain,

        product_id,
        line_of_business,
        coverage_code,

        accident_period,
        development_age_months,

        last_day(
            dateadd(
                month,
                development_age_months - 1,
                accident_period
            )
        ) as valuation_date,

        cumulative_reported_claim_count,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss

    from half_year_base

),


-- ============================================================
-- ANNUAL
--
-- Development ages:
-- 12, 24, 36, 48, ...
-- ============================================================

annual_base as (

    select
        product_id,
        line_of_business,
        coverage_code,

        accident_year as accident_period,

        development_age_annual
            as development_age_months,

        count(distinct claim_id)
            as cumulative_reported_claim_count,

        sum(cumulative_paid_loss)
            as cumulative_paid_loss,

        sum(cumulative_case_reserve)
            as cumulative_case_reserve,

        sum(cumulative_paid_expense)
            as cumulative_paid_expense,

        sum(cumulative_case_expense)
            as cumulative_case_expense,

        sum(cumulative_recovery)
            as cumulative_recovery,

        sum(cumulative_incurred_loss)
            as cumulative_incurred_loss

    from development

    where is_year_end = true
      and development_age_annual > 0

    group by
        product_id,
        line_of_business,
        coverage_code,
        accident_year,
        development_age_annual

),

annual_triangle as (

    select
        'annual' as triangle_grain,

        product_id,
        line_of_business,
        coverage_code,

        accident_period,
        development_age_months,

        last_day(
            dateadd(
                month,
                development_age_months - 1,
                accident_period
            )
        ) as valuation_date,

        cumulative_reported_claim_count,

        cumulative_paid_loss,
        cumulative_case_reserve,
        cumulative_paid_expense,
        cumulative_case_expense,
        cumulative_recovery,
        cumulative_incurred_loss

    from annual_base

)

-- ===============================================================================
-- Grain:
-- 1 row = triangle grain × product × coverage × accident period × development age
-- ===============================================================================

select * from monthly_triangle

union all

select * from quarterly_triangle

union all

select * from half_year_triangle

union all

select * from annual_triangle
