from support_poc.contracts import ComponentRef, FailureCode


class AdapterError(RuntimeError):
    def __init__(self, code: FailureCode, component: ComponentRef, message: str):
        super().__init__(message)
        self.code = code
        self.component = component
