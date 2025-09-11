import asyncio
import concurrent.futures
import contextvars
import inspect
import threading
from typing import Any, Callable, Optional
from queue import Queue, Empty
from dataclasses import dataclass

from tramp.optionals import Optional as TrampOptional


@dataclass
class AsyncHookRequest:
    """Request to execute an async hook function."""
    hook_func: Callable
    container: Any
    value: Any
    context: dict[str, Any]
    context_snapshot: contextvars.Context
    future: concurrent.futures.Future


class AsyncHookExecutor:
    """Manages async hook execution in a dedicated thread with event loop."""
    
    _instance: Optional["AsyncHookExecutor"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._request_queue = Queue()
        self._shutdown_event = threading.Event()
        self._started = False
        
    @classmethod
    def get_instance(cls) -> "AsyncHookExecutor":
        """Get or create the singleton executor instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._start()
        return cls._instance
    
    def _start(self):
        """Start the executor thread and event loop."""
        if self._started:
            return
            
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        self._started = True
    
    def _run_event_loop(self):
        """Run the event loop in the dedicated thread."""
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._loop = asyncio.get_event_loop()
        
        async def process_requests():
            while not self._shutdown_event.is_set():
                try:
                    # Check for requests with timeout
                    request = self._request_queue.get(timeout=0.1)
                    await self._process_request(request)
                except Empty:
                    continue
                except Exception as e:
                    # Log error but keep processing
                    print(f"Error processing async hook request: {e}")
        
        self._loop.run_until_complete(process_requests())
        self._loop.close()
    
    async def _process_request(self, request: AsyncHookRequest):
        """Process a single async hook request."""
        try:
            # Copy context vars to async thread
            # We'll run the hook in a task with the captured context
            task = asyncio.create_task(
                self._run_hook_with_context(
                    request.hook_func,
                    request.container,
                    request.value,
                    request.context,
                    request.context_snapshot
                )
            )
            result = await task
            request.future.set_result(result)
        except Exception as e:
            request.future.set_exception(e)
    
    async def _run_hook_with_context(self, hook_func: Callable, container: Any, 
                                    value: Any, context: dict[str, Any],
                                    context_snapshot: contextvars.Context):
        """Run hook with captured context vars."""
        # Apply context snapshot to current task
        for var, val in context_snapshot.items():
            var.set(val)
        
        return await self._call_async_hook(hook_func, container, value, context)
    
    async def _call_async_hook(self, hook_func: Callable, container: Any, value: Any, context: dict[str, Any]):
        """Call the async hook function with appropriate signature."""
        # Get function signature
        sig = inspect.signature(hook_func)
        params = list(sig.parameters.keys())
        
        # Check parameter count for backward compatibility
        if len(params) >= 3:
            # New style with context
            return await hook_func(container, value, context)
        else:
            # Legacy style without context
            return await hook_func(container, value)
    
    def run_async_hook(self, hook_func: Callable, container: Any, value: Any, 
                      context: dict[str, Any], context_snapshot: contextvars.Context) -> Any:
        """Execute an async hook and wait for result."""
        if not self._started:
            self._start()
        
        future = concurrent.futures.Future()
        request = AsyncHookRequest(
            hook_func=hook_func,
            container=container,
            value=value,
            context=context,
            context_snapshot=context_snapshot,
            future=future
        )
        
        self._request_queue.put(request)
        
        # Wait for async execution to complete
        try:
            return future.result(timeout=30)  # 30 second timeout for hooks
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Async hook {hook_func.__name__} timed out after 30 seconds")
    
    def shutdown(self):
        """Shutdown the executor and clean up resources."""
        if self._started:
            self._shutdown_event.set()
            if self._thread:
                self._thread.join(timeout=5)
            self._started = False


def is_async_hook(hook_func: Callable) -> bool:
    """Check if a hook function is async."""
    # Handle wrapped functions
    func = hook_func.func if hasattr(hook_func, 'func') else hook_func
    return inspect.iscoroutinefunction(func)


def call_hook_sync_or_async(hook_func: Callable, container: Any, value: Any, 
                           context: dict[str, Any]) -> Any:
    """Call a hook function, handling both sync and async variants."""
    if is_async_hook(hook_func):
        # Capture current context and run async hook
        context_snapshot = contextvars.copy_context()
        executor = AsyncHookExecutor.get_instance()
        return executor.run_async_hook(hook_func, container, value, context, context_snapshot)
    else:
        # Call sync hook directly
        return hook_func(container, value, context)