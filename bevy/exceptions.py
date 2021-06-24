class CanOnlyInjectIntoInjectables(Exception):
    """Raised when attempting to inject into an instance that is not an instance of injectable."""

    pass


class UnsupportedDependencyType(Exception):
    """Raised when attempting to add a dependency that doesn't match any known dependency type."""

    pass


class NoDependencyMatchesRequirement(Exception):
    """Raised no dependency matches the requirement."""

    pass
