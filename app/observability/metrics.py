"""Process-local lightweight metrics collector and registry."""

import threading
from typing import Any


class MetricsCollector:
    """Thread-safe, process-local in-memory metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {
            "http_requests_total": 0,
            "http_request_errors_total": 0,
            "llm_requests_total": 0,
            "llm_errors_total": 0,
            "cache_hits_total": 0,
            "cache_misses_total": 0,
            "cache_errors_total": 0,
            "persistence_operations_total": 0,
            "persistence_errors_total": 0,
        }
        self._timings: dict[str, list[float]] = {
            "llm_latency_ms": [],
            "http_duration_ms": [],
            "persistence_duration_ms": [],
        }

    def increment(self, counter_name: str, value: int = 1) -> None:
        """Increment a counter by value (thread-safe)."""
        with self._lock:
            if counter_name not in self._counters:
                self._counters[counter_name] = 0
            self._counters[counter_name] += value

    def record_timing(self, timing_name: str, duration_ms: float) -> None:
        """Record a latency measurement in milliseconds (capped buffer)."""
        with self._lock:
            if timing_name not in self._timings:
                self._timings[timing_name] = []
            # Keep rolling window of last 1000 measurements per metric
            if len(self._timings[timing_name]) >= 1000:
                self._timings[timing_name].pop(0)
            self._timings[timing_name].append(duration_ms)

    def get_snapshot(self) -> dict[str, Any]:
        """Produce an immutable snapshot of collected metrics."""
        with self._lock:
            snapshot: dict[str, Any] = {
                "counters": dict(self._counters),
                "summary": {},
            }
            for name, timings in self._timings.items():
                if timings:
                    snapshot["summary"][name] = {
                        "count": len(timings),
                        "avg_ms": round(sum(timings) / len(timings), 2),
                        "min_ms": round(min(timings), 2),
                        "max_ms": round(max(timings), 2),
                        "p95_ms": round(sorted(timings)[int(len(timings) * 0.95)], 2),
                    }
                else:
                    snapshot["summary"][name] = {"count": 0, "avg_ms": 0.0}
            return snapshot

    def reset(self) -> None:
        """Reset all metrics (primarily for test isolation)."""
        with self._lock:
            for k in self._counters:
                self._counters[k] = 0
            for k in self._timings:
                self._timings[k].clear()


# Process-level singleton instance
metrics = MetricsCollector()
