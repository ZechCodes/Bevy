#!/usr/bin/env python3
"""Test script to reproduce the qualifier resolution bug."""

from bevy import Container, Registry, injectable, Inject
from bevy.injection_types import Options


class Database:
    def __init__(self, name: str):
        self.name = name
    
    def __repr__(self):
        return f"Database({self.name})"


@injectable
def process_data(
    primary_db: Inject[Database, Options(qualifier="primary")],
    backup_db: Inject[Database, Options(qualifier="backup")]
):
    return f"Using {primary_db} and {backup_db}"


def main():
    """Test the qualifier resolution issue."""
    registry = Registry()
    container = Container(registry)
    
    # Add qualified dependencies
    container.add(Database, Database("primary_instance"), qualifier="primary") 
    container.add(Database, Database("backup_instance"), qualifier="backup")
    
    # Try to call the function - this should work but currently fails
    try:
        result = container.call(process_data)
        print(f"SUCCESS: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Error type: {type(e)}")
        
        # Check what's actually being passed to container.get
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()