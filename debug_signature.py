#!/usr/bin/env python3
"""Debug signature analysis."""

import inspect
from typing import get_type_hints
from bevy.injection_types import Inject, Options, extract_injection_info
from bevy.injections import analyze_function_signature, InjectionStrategy


class UserService:
    pass


def test_signature_analysis():
    """Debug the signature analysis process."""
    print("Debugging signature analysis...")
    
    def test_func(service: Inject[UserService]):
        return service
    
    # Get signature and type hints
    sig = inspect.signature(test_func)
    type_hints = get_type_hints(test_func, include_extras=True)
    
    print(f"Signature: {sig}")
    print(f"Type hints: {type_hints}")
    
    for param_name, param in sig.parameters.items():
        print(f"\nParameter: {param_name}")
        print(f"  Annotation: {param.annotation}")
        print(f"  From type_hints: {type_hints.get(param_name, 'NOT FOUND')}")
        
        # Test extraction
        annotation = type_hints.get(param_name, param.annotation)
        actual_type, options = extract_injection_info(annotation)
        print(f"  Extracted type: {actual_type}")
        print(f"  Extracted options: {options}")
    
    # Test full analysis
    injection_params = analyze_function_signature(test_func, InjectionStrategy.REQUESTED_ONLY)
    print(f"\nFull analysis result: {injection_params}")
    
    # Test with options
    def test_func_with_options(service: Inject[UserService, Options(qualifier="primary")]):
        return service
    
    injection_params2 = analyze_function_signature(test_func_with_options, InjectionStrategy.REQUESTED_ONLY)
    print(f"With options analysis: {injection_params2}")


if __name__ == "__main__":
    test_signature_analysis()