{{ config(severity='warn') }}

select *
from {{ ref('int_cdf_incurred') }}
where cdf < 1
