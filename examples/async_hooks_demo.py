#!/usr/bin/env python3
"""
Demonstration of async hook support in Bevy.

This example shows how to use async hooks for dependency injection,
including contextvar propagation across thread boundaries.
"""

import asyncio
import contextvars
from typing import Any

from tramp.optionals import Optional

from bevy import Registry, injectable, Inject
from bevy.hooks import hooks


# Example contextvar to demonstrate propagation
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default="")


class Database:
    """Mock database class for demonstration."""
    def __init__(self, connection_string: str = "sqlite:///:memory:"):
        self.connection_string = connection_string
        self.connected = False
    
    async def connect(self):
        """Simulate async database connection."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self.connected = True
        print(f"Connected to database: {self.connection_string}")
    
    async def query(self, sql: str):
        """Simulate async database query."""
        if not self.connected:
            raise RuntimeError("Database not connected")
        await asyncio.sleep(0.05)  # Simulate query delay
        return f"Results for: {sql}"


class UserService:
    """Service that depends on database."""
    def __init__(self, db: Database):
        self.db = db
    
    async def get_user(self, user_id: int):
        """Get user from database."""
        result = await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return f"User {user_id}: {result}"


def setup_async_hooks(registry: Registry):
    """Configure async hooks for the application."""
    
    @hooks.CREATE_INSTANCE
    async def async_database_factory(container, dependency, context):
        """Async factory for creating and connecting database instances."""
        if dependency == Database:
            print(f"[Async Hook] Creating database instance (request_id: {request_id_var.get()})")
            db = Database("postgresql://localhost/myapp")
            await db.connect()
            return Optional.Some(db)
        return Optional.Nothing()
    
    @hooks.INJECTION_REQUEST
    async def log_injection_request(container, context):
        """Log injection requests with context information."""
        await asyncio.sleep(0.01)  # Simulate async logging
        request_id = request_id_var.get()
        print(f"[Async Hook] Injecting {context.requested_type.__name__} for parameter '{context.parameter_name}' (request_id: {request_id})")
        return Optional.Nothing()
    
    @hooks.POST_INJECTION_CALL
    async def post_injection_metrics(container, context):
        """Collect metrics after function execution."""
        await asyncio.sleep(0.01)  # Simulate async metrics collection
        print(f"[Async Hook] Function '{context.function_name}' completed in {context.execution_time_ms:.2f}ms")
        return Optional.Nothing()
    
    # Register all hooks
    async_database_factory.register_hook(registry)
    log_injection_request.register_hook(registry)
    post_injection_metrics.register_hook(registry)


@injectable
def handle_user_request(user_id: int, service: Inject[UserService]):
    """Handler function that uses injected dependencies."""
    print(f"Processing request for user {user_id}")
    # For demo purposes, we'll use a sync handler
    # In a real async application, you would use async/await throughout
    return f"Processed user {user_id} with {service.__class__.__name__}"


def main():
    """Main entry point demonstrating async hooks."""
    print("=== Bevy Async Hooks Demo ===\n")
    
    # Create registry and configure hooks
    registry = Registry()
    setup_async_hooks(registry)
    
    # Add UserService factory
    registry.add_factory(lambda container: UserService(container.get(Database)), UserService)
    
    # Create container
    container = registry.create_container()
    
    # Simulate multiple requests with different context
    for i in range(1, 4):
        print(f"\n--- Request {i} ---")
        
        # Set request context
        request_id_var.set(f"req-{i:03d}")
        
        # Call the handler with injection
        # Note: In a real async application, you would use asyncio.run() or await
        # For this demo, we're using the sync container.call() which handles async hooks internally
        result = container.call(handle_user_request, user_id=i)
        print(f"Result: {result}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()