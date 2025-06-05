#!/usr/bin/env python3
"""Bevy documentation CLI interface.

Usage:
    python -m bevy <dotpath> [command]
    
    Commands:
        (default)   - Show docstring and file location
        signature   - Show function/class signature
        members     - Show members with signatures (for classes/modules)
        
Examples:
    python -m bevy bevy.containers.Container
    python -m bevy bevy.containers.Container.get signature
    python -m bevy bevy.containers members
"""

import argparse
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple


def parse_dotpath(dotpath: str) -> Tuple[object, str, Optional[object]]:
    """Parse a dotpath and return (module, attr_path, object).
    
    Args:
        dotpath: A dot-separated path like 'bevy.containers.Container.get'
        
    Returns:
        Tuple of (module, remaining_attr_path, resolved_object)
    """
    parts = dotpath.split('.')
    
    # Try importing progressively longer module paths
    last_import_error = None
    for i in range(len(parts), 0, -1):
        module_path = '.'.join(parts[:i])
        try:
            module = importlib.import_module(module_path)
            attr_path = '.'.join(parts[i:])
            
            # If no attributes to access, return the module itself
            if not attr_path:
                return module, '', module
                
            # Try to resolve the remaining path as attributes
            obj = module
            for attr in parts[i:]:
                obj = getattr(obj, attr)
            
            return module, attr_path, obj
            
        except ImportError as e:
            last_import_error = e
            continue
        except AttributeError:
            continue
    
    if last_import_error:
        raise ValueError(f"Could not resolve '{dotpath}': {last_import_error}")
    raise ValueError(f"Could not resolve '{dotpath}'")


def get_relative_path(obj: Any) -> Optional[str]:
    """Get the file path relative to the bevy directory."""
    try:
        file_path = inspect.getfile(obj)
        bevy_dir = Path(__file__).parent
        
        # Try to make the path relative to bevy directory
        try:
            rel_path = Path(file_path).relative_to(bevy_dir)
            return str(rel_path)
        except ValueError:
            # If not relative to bevy dir, return absolute path
            return file_path
    except TypeError:
            # Built-in or C extension
            return None


def format_annotation(annotation: Any) -> str:
    """Format a type annotation to show qualified names."""
    if annotation == inspect.Signature.empty:
        return ""
    
    # Handle string annotations (forward references)
    if isinstance(annotation, str):
        return annotation
    
    # Handle class types
    if inspect.isclass(annotation):
        module = annotation.__module__
        if module and module != "builtins":
            return f"{module}.{annotation.__qualname__}"
        return annotation.__qualname__
    
    # Handle module types
    if inspect.ismodule(annotation):
        return annotation.__name__
    
    # For other types, convert to string and clean up
    ann_str = str(annotation)
    
    # Handle ForwardRef
    if ann_str.startswith("ForwardRef("):
        # Extract the string inside ForwardRef('...')
        import re
        match = re.search(r"ForwardRef\('([^']+)'\)", ann_str)
        if match:
            return match.group(1)
    
    # Handle typing module representations
    if ann_str.startswith("typing."):
        # Try to clean up generic types with ForwardRef
        import re
        # Replace ForwardRef('ClassName') with just ClassName
        ann_str = re.sub(r"ForwardRef\('([^']+)'\)", r"\1", ann_str)
        return ann_str
    
    # Handle class representations like <class 'module.Class'>
    if ann_str.startswith("<class '") and ann_str.endswith("'>"):
        class_path = ann_str[8:-2]  # Extract the path between quotes
        return class_path
    
    return ann_str


def format_signature_line(name: str, sig: inspect.Signature, indent: int = 0) -> str:
    """Format a function signature, breaking long lines if needed."""
    # Build parameter strings with formatted annotations
    param_strs = []
    for param in sig.parameters.values():
        param_str = param.name
        
        # Add annotation if present
        if param.annotation != inspect.Parameter.empty:
            ann_str = format_annotation(param.annotation)
            param_str += f": {ann_str}"
        
        # Add default value if present
        if param.default != inspect.Parameter.empty:
            if isinstance(param.default, str):
                param_str += f" = {repr(param.default)}"
            else:
                param_str += f" = {param.default}"
        
        # Handle special parameter kinds
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            param_str = f"*{param_str}"
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            param_str = f"**{param_str}"
        
        param_strs.append(param_str)
    
    # Format return annotation
    return_annotation = ""
    if sig.return_annotation != inspect.Signature.empty:
        return_annotation = f" -> {format_annotation(sig.return_annotation)}"
    
    # Build the full signature
    params_str = ", ".join(param_strs)
    full_sig = f"{name}({params_str}){return_annotation}"
    
    # If it fits on one line, return it
    if len(full_sig) <= 80:
        return " " * indent + full_sig
    
    # Break into multiple lines
    lines = [" " * indent + f"{name}("]
    for i, param in enumerate(param_strs):
        line = " " * (indent + 4) + param
        if i < len(param_strs) - 1:
            line += ","
        lines.append(line)
    lines.append(" " * indent + f"){return_annotation}")
    
    return "\n".join(lines)


def format_signature(obj: Any) -> Optional[str]:
    """Get a formatted signature for a callable or class."""
    try:
        if inspect.isclass(obj):
            # For classes, show base classes and __init__ signature
            bases = obj.__bases__
            if bases and bases != (object,):
                # Format base classes, excluding object
                base_names = [base.__name__ for base in bases if base is not object]
                if base_names:
                    bases_str = f"({', '.join(base_names)})"
                else:
                    bases_str = ""
            else:
                bases_str = ""
            
            # Get __init__ signature
            try:
                sig = inspect.signature(obj.__init__)
                init_sig = format_signature_line("def __init__", sig, indent=4)
                return f"class {obj.__name__}{bases_str}:\n{init_sig}"
            except (ValueError, TypeError):
                # If __init__ signature is not available
                return f"class {obj.__name__}{bases_str}"
                
        elif inspect.isroutine(obj):
            name = getattr(obj, '__name__', str(obj))
            
            # Try to get overloads if available
            try:
                from typing import get_overloads
                overloads = get_overloads(obj)
                if overloads:
                    # Format each overload signature
                    signatures = []
                    for overload in overloads:
                        sig = inspect.signature(overload)
                        formatted = format_signature_line(name, sig)
                        signatures.append(f"@overload\n{formatted}")
                    # Also add the implementation signature
                    impl_sig = inspect.signature(obj)
                    formatted = format_signature_line(name, impl_sig)
                    signatures.append(formatted)
                    return "\n\n".join(signatures)
            except (ImportError, AttributeError):
                # typing.get_overloads not available (Python < 3.11)
                pass
            
            # Fallback to regular signature
            sig = inspect.signature(obj)
            return format_signature_line(name, sig)
    except (ValueError, TypeError):
        return None
    return None


def show_docstring(obj: Any, dotpath: str) -> None:
    """Display docstring and file location."""
    # Get docstring
    doc = inspect.getdoc(obj)
    if not doc:
        doc = "(No docstring available)"
    
    # Get file location
    file_path = get_relative_path(obj)
    
    print(f"Documentation for: {dotpath}")
    print(f"File: {file_path or '(built-in)'}")
    print()
    print(doc)


def show_signature(obj: Any, dotpath: str) -> None:
    """Display signature for a function or class."""
    sig = format_signature(obj)
    
    if sig:
        print(f"Signature for: {dotpath}")
        print(sig)
    else:
        print(f"No signature available for: {dotpath}")


def show_members(obj: Any, dotpath: str) -> None:
    """Display members with their signatures."""
    print(f"Members of: {dotpath}")
    print()
    
    members = []
    
    if inspect.ismodule(obj):
        # For modules, show all public members
        for name, member in inspect.getmembers(obj):
            if not name.startswith('_'):
                members.append((name, member))
    elif inspect.isclass(obj):
        # For classes, show methods and attributes
        for name, member in inspect.getmembers(obj):
            if not name.startswith('_') or name in ('__init__', '__call__'):
                members.append((name, member))
    else:
        print("Object is not a module or class")
        return
    
    # Sort and display members
    members.sort(key=lambda x: x[0])
    
    for name, member in members:
        if inspect.isclass(member):
            # For nested classes, show a simplified signature
            bases = member.__bases__
            if bases and bases != (object,):
                base_names = [base.__name__ for base in bases if base is not object]
                if base_names:
                    print(f"  class {name}({', '.join(base_names)})")
                else:
                    print(f"  class {name}")
            else:
                print(f"  class {name}")
        elif inspect.isroutine(member):
            sig = format_signature(member)
            if sig:
                print(f"  {sig}")
            else:
                print(f"  {name}")
        else:
            # For non-callable attributes
            type_name = type(member).__name__
            print(f"  {name}: {type_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Bevy documentation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'dotpath',
        help='Dot-separated path to module, class, or function'
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['signature', 'members'],
        help='Command to execute (default: show docstring)'
    )
    
    args = parser.parse_args()
    
    try:
        module, attr_path, obj = parse_dotpath(args.dotpath)
        
        if args.command == 'signature':
            show_signature(obj, args.dotpath)
        elif args.command == 'members':
            show_members(obj, args.dotpath)
        else:  # default: docstring (None or any other value)
            show_docstring(obj, args.dotpath)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()