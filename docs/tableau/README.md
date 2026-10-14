# Tableau Dashboard Layer

This project exposes three dbt marts intended for Tableau or Power BI connection
through Snowflake:

- `TABLEAU_PRICING_DASHBOARD`: primary pricing output by approved selection,
  triangle grain, development pool, and line of business.
- `TABLEAU_TRIANGLE_DIAGNOSTICS`: pooled triangle values for actuarial
  heatmaps and incurred reconciliation.
- `TABLEAU_CONTROL_DASHBOARD`: reconciliation and governance checks.

Suggested Tableau worksheets:

- Rate indication by development pool: use `indicated_rate_change`,
  `current_average_premium`, and `indicated_premium`.
- Pure premium bridge: compare `untrended_pure_premium`,
  `trended_pure_premium`, `trend_impact_on_pure_premium`, and
  `expense_and_profit_impact`.
- Triangle heatmap: use `accident_period`, `development_age_months`, and
  `cumulative_incurred_loss`.
- Control monitor: use `metric_name`, `absolute_difference`,
  `percentage_difference`, and `control_status`.

Recommended filters:

- `selection_version_id`
- `triangle_grain`
- `line_of_business`
- `development_pool_id`
- `control_status`
