#!/usr/bin/env python3
"""
Example demonstrating the new CircularDependencyError.

This shows how circular dependencies are detected and the rich error information provided.
"""

# Example circular dependency scenario
class ServiceA:
    def __init__(self, service_b):
        self.service_b = service_b

class ServiceB:
    def __init__(self, service_c):
        self.service_c = service_c

class ServiceC:
    def __init__(self, service_a):
        self.service_a = service_a

# Factory functions that create the circular dependency
def create_service_a(container):
    service_b = container.get(ServiceB)
    return ServiceA(service_b)

def create_service_b(container):
    service_c = container.get(ServiceC)
    return ServiceB(service_c)

def create_service_c(container):
    service_a = container.get(ServiceA)
    return ServiceC(service_a)

def demonstrate_circular_dependency_error():
    """Show how CircularDependencyError provides rich debugging information."""
    from bevy import Registry, Container, CircularDependencyError, DependencyResolutionError
    
    # Set up the circular dependency
    registry = Registry()
    registry.add_factory(create_service_a, ServiceA)
    registry.add_factory(create_service_b, ServiceB)
    registry.add_factory(create_service_c, ServiceC)
    container = registry.create_container()
    
    try:
        # This will trigger circular dependency detection
        container.get(ServiceA)
    except CircularDependencyError as e:
        print("CircularDependencyError caught!")
        print(f"Error message: {e}")
        print(f"Dependency cycle: {[t.__name__ for t in e.dependency_cycle]}")
        print(f"Cycle description: {e.cycle_description}")
        print(f"Dependency type: {e.dependency_type.__name__}")
        print(f"Parameter name: {e.parameter_name}")
        print()
        print("This error inherits from DependencyResolutionError, so it can be caught generically:")
        print(f"Is instance of DependencyResolutionError: {isinstance(e, DependencyResolutionError)}")
        
    except DependencyResolutionError as e:
        print("This would catch CircularDependencyError too!")
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Demonstrating CircularDependencyError:")
    print("=" * 50)
    demonstrate_circular_dependency_error()