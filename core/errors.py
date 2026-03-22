class InfeasibleError(Exception):

    def __init__(self, reasons: list[str]) -> None:
        if not reasons:
            reasons = ["No feasible schedule exists under the given constraints."]
        self.reasons = reasons
        super().__init__(reasons[0])
