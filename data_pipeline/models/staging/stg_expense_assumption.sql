select

    state as state_grp,
    risk_class as risk_class_grp,
    vehicle_segment as vehicle_segment_grp,
    fixed_expense_per_exposure,
    variable_expense_ratio,
    ulae_ratio,
    profit_ratio

from {{ source('actuarial_input', 'expense_assumption')
