"""Small in-process cache so a preview and its downloads share one extraction."""

import threading
import time
from collections import OrderedDict
from collections.abc import Callable

from app.media import ExtractedMedia


class ResultCache:
    def __init__(
        self,
        ttl_seconds: float,
        max_entries: int = 64,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._items: OrderedDict[str, tuple[float, ExtractedMedia]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> ExtractedMedia | None:
        now = self.clock()
        with self._lock:
            found = self._items.get(key)
            if found is None:
                return None
            stored_at, value = found
            if now - stored_at > self.ttl_seconds:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value: ExtractedMedia) -> None:
        now = self.clock()
        with self._lock:
            self._items[key] = (now, value)
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)
