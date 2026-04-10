with cl_incurred as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        'Chain_ladder_incurred' as method,
        ultimate_loss
    from {{ ref('int_ultimate_incurred_CL') }}

),

cl_paid as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        'Chain_ladder_paid' as method,
        ultimate_loss
    from {{ ref('int_ultimate_paid_CL') }}

),

actuarial_input as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        method,
        ultimate_loss

    from {{ ref('stg_selected_ultimate_loss') }}

)

select * from cl_incurred
union all
select * from cl_paid
union all
select * from actuarial_input
