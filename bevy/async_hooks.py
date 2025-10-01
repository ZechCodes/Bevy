"""Utilities for async hook support."""
import inspect
from typing import Callable


def is_async_hook(hook_func: Callable) -> bool:
    """Check if a hook function is async."""
    # Handle wrapped functions
    func = hook_func.func if hasattr(hook_func, 'func') else hook_func
    return inspect.iscoroutinefunction(func)
