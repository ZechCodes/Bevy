#!/usr/bin/env python3
"""Quick test script for injection_types module."""

from bevy.injection_types import (
    Inject, Options, InjectionStrategy, TypeMatchingStrategy,
    extract_injection_info, is_optional_type, get_non_none_type
)


class UserService:
    pass


class Database:
    pass


def test_inject_type_alias():
    """Test the Inject type alias works correctly."""
    print("Testing Inject type alias...")
    
    # Test basic Inject usage
    def func1(service: Inject[UserService]): pass
    def func2(service: Inject[UserService, Options(qualifier="primary")]): pass
    
    # Extract info from annotations
    _, sig1 = func1.__annotations__.popitem()
    _, sig2 = func2.__annotations__.popitem()
    
    type1, opts1 = extract_injection_info(sig1)
    type2, opts2 = extract_injection_info(sig2)
    
    print(f"  func1: type={type1}, options={opts1}")
    print(f"  func2: type={type2}, options={opts2}")
    
    assert type1 == UserService
    assert opts1 is None
    assert type2 == UserService
    assert opts2.qualifier == "primary"
    print("  ✓ Inject type alias works correctly")


def test_optional_types():
    """Test optional type detection."""
    print("\nTesting optional type detection...")
    
    def func1(service: UserService): pass
    def func2(service: UserService | None): pass
    def func3(service: Inject[UserService]): pass
    def func4(service: Inject[UserService | None]): pass
    
    # Test regular types
    _, sig1 = func1.__annotations__.popitem()
    _, sig2 = func2.__annotations__.popitem()
    _, sig3 = func3.__annotations__.popitem()
    _, sig4 = func4.__annotations__.popitem()
    
    print(f"  UserService optional: {is_optional_type(sig1)}")
    print(f"  UserService | None optional: {is_optional_type(sig2)}")
    
    # Extract from Inject types
    type3, _ = extract_injection_info(sig3)
    type4, _ = extract_injection_info(sig4)
    
    print(f"  Inject[UserService] optional: {is_optional_type(type3)}")
    print(f"  Inject[UserService | None] optional: {is_optional_type(type4)}")
    
    # Test non-None type extraction
    non_none2 = get_non_none_type(sig2)
    non_none4 = get_non_none_type(type4)
    
    print(f"  Non-None from UserService | None: {non_none2}")
    print(f"  Non-None from Inject[UserService | None]: {non_none4}")
    
    assert not is_optional_type(sig1)
    assert is_optional_type(sig2)
    assert not is_optional_type(type3)
    assert is_optional_type(type4)
    assert non_none2 == UserService
    assert non_none4 == UserService
    print("  ✓ Optional type detection works correctly")


def test_options():
    """Test Options class."""
    print("\nTesting Options class...")
    
    opts1 = Options()
    opts2 = Options(qualifier="primary")
    opts3 = Options(qualifier="cache", from_config="redis.url")
    
    print(f"  Empty options: {opts1}")
    print(f"  With qualifier: {opts2}")
    print(f"  With qualifier and config: {opts3}")
    
    assert opts1.qualifier is None
    assert opts2.qualifier == "primary"
    assert opts3.qualifier == "cache"
    assert opts3.from_config == "redis.url"
    print("  ✓ Options class works correctly")


def test_enums():
    """Test enum definitions."""
    print("\nTesting enums...")
    
    # Test injection strategies
    assert InjectionStrategy.DEFAULT.value == "default"
    assert InjectionStrategy.REQUESTED_ONLY.value == "requested_only"
    print(f"  InjectionStrategy.DEFAULT: {InjectionStrategy.DEFAULT}")
    
    # Test type matching strategies  
    assert TypeMatchingStrategy.DEFAULT.value == "default"
    assert TypeMatchingStrategy.SUBCLASS.value == "subclass"
    print(f"  TypeMatchingStrategy.DEFAULT: {TypeMatchingStrategy.DEFAULT}")
    
    print("  ✓ Enums work correctly")


if __name__ == "__main__":
    test_inject_type_alias()
    test_optional_types()
    test_options()
    test_enums()
    print("\n🎉 All tests passed!")