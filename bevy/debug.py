"""
Debug utilities for the Bevy dependency injection system.
"""


class DebugLogger:
    """
    Centralized debug logging for dependency injection.
    
    Provides clean debug logging without cluttering the main code
    with if statements everywhere.
    """
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    
    def log(self, message: str):
        """Log a debug message if debugging is enabled."""
        if self.enabled:
            print(f"[BEVY DEBUG] {message}")
    
    def resolving_dependency(self, param_type: type, options=None):
        """Log dependency resolution start."""
        if self.enabled:
            opts_str = f" with options {options}" if options else ""
            print(f"[BEVY DEBUG] Resolving {param_type}{opts_str}")
    
    def resolving_qualified(self, param_type: type, qualifier: str):
        """Log qualified dependency resolution."""
        if self.enabled:
            print(f"[BEVY DEBUG] Resolving qualified {param_type} with qualifier '{qualifier}'")
    
    def using_default_factory(self, param_type: type):
        """Log default factory usage."""
        if self.enabled:
            print(f"[BEVY DEBUG] Using default factory for {param_type}")
    
    def optional_dependency_none(self, param_name: str):
        """Log optional dependency returning None."""
        if self.enabled:
            print(f"[BEVY DEBUG] Optional dependency {param_name} not found, using None")
    
    def non_strict_mode_none(self, param_name: str):
        """Log non-strict mode returning None."""
        if self.enabled:
            print(f"[BEVY DEBUG] Non-strict mode: {param_name} not found, using None")
    
    def injected_parameter(self, param_name: str, param_type: type, value):
        """Log successful parameter injection."""
        if self.enabled:
            print(f"[BEVY DEBUG] Injected {param_name}: {param_type} = {value}")


# Global debug logger instance
_debug_logger = DebugLogger()


def get_debug_logger() -> DebugLogger:
    """Get the global debug logger instance."""
    return _debug_logger


def set_debug_enabled(enabled: bool):
    """Enable or disable debug logging globally."""
    _debug_logger.enabled = enabled


def create_debug_logger(enabled: bool) -> DebugLogger:
    """Create a new debug logger with specified state."""
    return DebugLogger(enabled)