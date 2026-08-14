with expected as (

    select
        c.coverage_id,
        greatest(c.effective_date, p.effective_date, r.effective_date) as expected_effective_date,
        c.expiration_date as expected_scheduled_expiration_date,
        least(
            c.expiration_date,
            p.expiration_date,
            coalesce(p.cancellation_date, p.expiration_date),
            r.expiration_date
        ) as expected_actual_expiration_date
    from {{ ref('stg_policy_coverage') }} c
    join {{ ref('stg_policy') }} p
        on c.policy_id = p.policy_id
    join {{ ref('stg_policy_risk_unit') }} r
        on c.policy_id = r.policy_id
       and c.risk_unit_id = r.risk_unit_id

),

actual as (

    select *
    from {{ ref('int_coverage_active_period') }}

)

select
    e.coverage_id,
    e.expected_effective_date,
    a.coverage_effective_date,
    e.expected_scheduled_expiration_date,
    a.scheduled_expiration_date,
    e.expected_actual_expiration_date,
    a.actual_expiration_date
from expected e
left join actual a
    on e.coverage_id = a.coverage_id
where e.expected_actual_expiration_date > e.expected_effective_date
  and (
      a.coverage_id is null
      or a.coverage_effective_date != e.expected_effective_date
      or a.scheduled_expiration_date != e.expected_scheduled_expiration_date
      or a.actual_expiration_date != e.expected_actual_expiration_date
  )
