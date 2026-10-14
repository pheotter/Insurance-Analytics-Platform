"""Application errors mapped to API responses by the HTTP layer."""


class WorkflowError(RuntimeError):
    pass


class WorkflowNotFoundError(WorkflowError):
    pass


class WorkflowValidationError(WorkflowError):
    pass


class InvalidTransitionError(WorkflowError):
    pass
