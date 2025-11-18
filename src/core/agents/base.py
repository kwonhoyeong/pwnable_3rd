"""Base agent class and protocols for consistent agent implementations."""

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from common_lib.cache import AsyncCache

ProgressCallback = Callable[[str, str], None]
T = TypeVar("T")


class BaseAgent(ABC):
    """Base class for all pipeline agents with common caching and fallback patterns."""

    def __init__(self, cache: AsyncCache, step_name: str) -> None:
        """
        Initialize agent with cache and step identifier.

        Args:
            cache: AsyncCache instance for result caching
            step_name: Human-readable step name for progress callbacks (e.g., "MAPPING", "EPSS")
        """
        self._cache = cache
        self._step_name = step_name

    async def _get_cached(self, cache_key: str, force: bool = False) -> Optional[Any]:
        """
        Retrieve value from cache if force flag is not set.

        Args:
            cache_key: Cache key to retrieve
            force: If True, bypass cache

        Returns:
            Cached value or None if not found/forced
        """
        if force:
            return None
        return await self._cache.get(cache_key)

    async def _set_cache(self, cache_key: str, value: Any) -> None:
        """
        Store value in cache.

        Args:
            cache_key: Cache key to store under
            value: Value to cache
        """
        await self._cache.set(cache_key, value)

    def _progress(self, message: str, progress_cb: ProgressCallback) -> None:
        """
        Send progress update.

        Args:
            message: Progress message
            progress_cb: Progress callback
        """
        progress_cb(self._step_name, message)

    @abstractmethod
    async def execute(
        self, force: bool = False, progress_cb: Optional[ProgressCallback] = None
    ) -> Any:
        """
        Execute agent logic.

        Implementations should:
        1. Check cache (unless force=True)
        2. Execute service call if needed (use _safe_call for fallback handling)
        3. Update cache
        4. Return result

        Args:
            force: If True, bypass cache and force fresh execution
            progress_cb: Optional callback for progress updates

        Returns:
            Agent result (type varies by agent)
        """
        pass


class SingleItemAgent(BaseAgent):
    """
    Base class for agents that process a single item.

    Typical flow:
    1. Check cache
    2. If cache miss: call service
    3. Store in cache
    4. Return single result object
    """

    pass


class BatchAgent(BaseAgent):
    """
    Base class for agents that process multiple items with batch optimization.

    Typical flow:
    1. Load all items from cache if available
    2. Identify missing items
    3. Fetch only missing items from service
    4. Merge cached + fresh results
    5. Update cache with full results
    6. Return merged results dict
    """

    pass
