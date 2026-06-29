class MovaContractPluginError(Exception):
    pass


class PackageValidationError(MovaContractPluginError):
    pass


class ContractViolation(MovaContractPluginError):
    pass


class StepOrderViolation(ContractViolation):
    pass


class FinalDecisionViolation(ContractViolation):
    pass


class BindingViolation(PackageValidationError):
    pass


class ClassificationViolation(PackageValidationError):
    pass
