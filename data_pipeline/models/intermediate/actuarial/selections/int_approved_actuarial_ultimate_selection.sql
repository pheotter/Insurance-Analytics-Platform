with approved_version as (

    select selection_version_id
    from {{ ref('stg_actuarial_selection_version') }}
    where status = 'APPROVED'
      and selection_version_id = '{{ var("selection_version_id", "__selection_version_required__") }}'

),

selection as (

    select s.*
    from {{ ref('stg_actuarial_ultimate_selection') }} s
    inner join approved_version v
        on s.selection_version_id = v.selection_version_id

)

select *
from selection
