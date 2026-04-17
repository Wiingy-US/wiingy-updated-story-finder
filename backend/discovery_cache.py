import time
import threading

_cache = {
    "data": None,
    "cached_at": None,
    "ttl_seconds": 1800  # 30 minutes
}
_lock = threading.Lock()


def get_cached_discovery():
    with _lock:
        if _cache["data"] is None:
            return None
        age = time.time() - _cache["cached_at"]
        if age > _cache["ttl_seconds"]:
            return None
        return _cache["data"]


def set_cached_discovery(data):
    with _lock:
        _cache["data"] = data
        _cache["cached_at"] = time.time()


def get_cache_age_seconds():
    with _lock:
        if _cache["cached_at"] is None:
            return None
        return int(time.time() - _cache["cached_at"])
