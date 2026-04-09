with ratios as (
    select *
    from {{ ref('int_ldf_raw') }}
    where link_ratio_incurred is not null
),

summary as (
    select
        count(*) as total_rows,
        sum(case when link_ratio_incurred >= 1 then 1 else 0 end) as valid_rows
    from ratios
)

select *
from summary
where total_rows > 0
  and valid_rows / total_rows::float < 0.90
