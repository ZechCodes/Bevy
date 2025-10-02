"""Test that parameter defaults are properly tracked in InjectionContext."""

import pytest
from tramp.optionals import Optional
from bevy import Container, Registry, injectable, Inject
from bevy.hooks import Hook, InjectionContext, hooks


class TestParameterDefaults:
    """Test suite for parameter default tracking in InjectionContext."""

    def test_no_default_tracked_as_nothing(self):
        """Test that parameters without defaults are tracked as Optional.Nothing()."""
        captured_contexts = []
        
        @hooks.INJECTION_REQUEST
        def capture_context(container: Container, context: InjectionContext):
            captured_contexts.append(context)
            return Optional.Nothing()
        
        registry = Registry()
        capture_context.register_hook(registry)
        container = Container(registry)
        
        class Service:
            pass
        
        @injectable
        def func_no_default(service: Inject[Service]):
            return service
        
        container.add(Service())
        container.call(func_no_default)
        
        assert len(captured_contexts) == 1
        context = captured_contexts[0]
        assert isinstance(context.parameter_default, Optional.Nothing)
    
    def test_none_default_tracked_as_some_none(self):
        """Test that None defaults are tracked as Optional.Some(None)."""
        captured_contexts = []
        
        @hooks.INJECTION_REQUEST
        def capture_context(container: Container, context: InjectionContext):
            captured_contexts.append(context)
            return Optional.Nothing()
        
        registry = Registry()
        capture_context.register_hook(registry)
        container = Container(registry)
        
        class Service:
            pass
        
        @injectable
        def func_none_default(service: Inject[Service] = None):
            return service
        
        container.add(Service())
        container.call(func_none_default)
        
        assert len(captured_contexts) == 1
        context = captured_contexts[0]
        assert isinstance(context.parameter_default, Optional.Some)
        assert context.parameter_default.value is None
    
    def test_object_default_tracked_as_some_value(self):
        """Test that object defaults are tracked as Optional.Some(object)."""
        captured_contexts = []
        
        @hooks.INJECTION_REQUEST
        def capture_context(container: Container, context: InjectionContext):
            captured_contexts.append(context)
            return Optional.Nothing()
        
        registry = Registry()
        capture_context.register_hook(registry)
        container = Container(registry)
        
        class Service:
            pass
        
        default_service = Service()
        
        @injectable
        def func_with_default(service: Inject[Service] = default_service):
            return service
        
        container.add(Service())  # Add different instance to container
        container.call(func_with_default)
        
        assert len(captured_contexts) == 1
        context = captured_contexts[0]
        assert isinstance(context.parameter_default, Optional.Some)
        assert context.parameter_default.value is default_service
    
    def test_multiple_parameters_with_mixed_defaults(self):
        """Test that multiple parameters with different default types are tracked correctly."""
        captured_contexts = []
        
        @hooks.INJECTION_REQUEST
        def capture_context(container: Container, context: InjectionContext):
            captured_contexts.append(context)
            return Optional.Nothing()
        
        registry = Registry()
        capture_context.register_hook(registry)
        container = Container(registry)
        
        class ServiceA:
            pass
        
        class ServiceB:
            pass
        
        class ServiceC:
            pass
        
        default_b = ServiceB()
        
        @injectable
        def func_mixed(
            a: Inject[ServiceA],  # No default
            b: Inject[ServiceB] = default_b,  # Object default
            c: Inject[ServiceC] = None  # None default
        ):
            return (a, b, c)
        
        container.add(ServiceA())
        container.add(ServiceB())
        container.add(ServiceC())
        container.call(func_mixed)
        
        assert len(captured_contexts) == 3
        
        # Check parameter 'a' - no default
        context_a = next(ctx for ctx in captured_contexts if ctx.parameter_name == 'a')
        assert isinstance(context_a.parameter_default, Optional.Nothing)
        
        # Check parameter 'b' - object default
        context_b = next(ctx for ctx in captured_contexts if ctx.parameter_name == 'b')
        assert isinstance(context_b.parameter_default, Optional.Some)
        assert context_b.parameter_default.value is default_b
        
        # Check parameter 'c' - None default
        context_c = next(ctx for ctx in captured_contexts if ctx.parameter_name == 'c')
        assert isinstance(context_c.parameter_default, Optional.Some)
        assert context_c.parameter_default.value is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])