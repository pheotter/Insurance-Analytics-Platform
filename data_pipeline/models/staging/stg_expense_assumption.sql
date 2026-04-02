select

    pricing_version,
    state as state_grp,
    fixed_expense_per_exposure,
    variable_expense_ratio,
    ulae_ratio,
    profit_ratio,
    target_loss_ratio

from {{ source('actuarial_input', 'expense_assumption') }}
