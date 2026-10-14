with cl_claim_count as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        'Chain_ladder' as method,
        ultimate_claim_count
    from {{ ref('int_ultimate_claim_count_CL') }}

),

actuarial_input as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        method,
        ultimate_claim_count

    from {{ ref('stg_selected_ultimate_claim_count') }}

)

select * from cl_claim_count
union all
select * from actuarial_input
