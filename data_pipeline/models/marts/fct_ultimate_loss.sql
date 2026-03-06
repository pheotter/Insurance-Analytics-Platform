with cl_loss as (

    select
        state_grp,
        risk_class_grp,
        vehicle_segment_grp,
        accident_year,
        'Chain_ladder' as method,
        ultimate_loss
    from {{ ref('int_ultimate_loss_CL') }}

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

select * from cl_loss
union all
select * from actuarial_input
