import time
import logging
import functools
import inspect
from typing import Callable, Any

logger = logging.getLogger(__name__)


def _get_function_name(func: Callable, args: tuple = ()) -> str:
    """
    Get the full qualified name of a function.
    For methods, tries to get the actual class name from the instance at runtime.
    Returns 'ClassName.method_name' for methods, or 'function_name' for functions.
    """
    # Try to get the actual class from the instance (for methods)
    if args and len(args) > 0:
        instance = args[0]
        # Check if it's a bound method (has self or cls)
        if inspect.ismethod(func) or (hasattr(instance, '__class__') and not inspect.isclass(instance)):
            # Get the actual class of the instance
            actual_class = instance.__class__
            method_name = func.__name__
            return f"{actual_class.__name__}.{method_name}"
        elif inspect.isclass(instance):
            # It's a classmethod, instance is actually the class
            method_name = func.__name__
            return f"{instance.__name__}.{method_name}"
    
    # Fallback to __qualname__ (works for functions and when we can't determine the class)
    return func.__qualname__


def log_execution_time(log_level: str = "info", unit: str = "ms") -> Callable:
    """
    Decorator to measure and log the execution time.
    
    For methods, it will log the actual class name (even if decorated on an abstract class).
    
    Args:
        log_level: Log level ("debug", "info", "warning", "error")
        unit: Time unit ("ms" for milliseconds, "s" for seconds)
    """
    def decorator(func: Callable) -> Callable:
        base_func_name = func.__qualname__  # Fallback name
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            func_name = _get_function_name(func, args) or base_func_name
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000 if unit == "ms" else (time.time() - start_time)
                getattr(logger, log_level)(f"{func_name} executed in {elapsed:.2f}{unit}")
                return result
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000 if unit == "ms" else (time.time() - start_time)
                logger.error(f"{func_name} failed after {elapsed:.2f}{unit}: {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            func_name = _get_function_name(func, args) or base_func_name
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000 if unit == "ms" else (time.time() - start_time)
                getattr(logger, log_level)(f"{func_name} executed in {elapsed:.2f}{unit}")
                return result
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000 if unit == "ms" else (time.time() - start_time)
                logger.error(f"{func_name} failed after {elapsed:.2f}{unit}: {e}")
                raise
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    
    return decorator