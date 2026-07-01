"""Lightweight in-process metrics for monitoring.

Tracks the signals the PRD calls out — query latency, token usage, and failed
answers — without pulling in a full metrics backend. For production you'd export these
to Prometheus/OpenTelemetry; the collector interface stays the same.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Metrics:
    rag_queries: int = 0
    failed_answers: int = 0
    total_tokens: int = 0
    _latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=500))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_query(self, *, latency_ms: float, tokens: int, grounded: bool) -> None:
        with self._lock:
            self.rag_queries += 1
            self.total_tokens += tokens
            self._latencies_ms.append(latency_ms)
            if not grounded:
                self.failed_answers += 1

    def snapshot(self) -> dict:
        with self._lock:
            lat = list(self._latencies_ms)
        lat_sorted = sorted(lat)

        def pct(p: float) -> float:
            if not lat_sorted:
                return 0.0
            idx = min(len(lat_sorted) - 1, int(p / 100 * len(lat_sorted)))
            return round(lat_sorted[idx], 1)

        return {
            "rag_queries": self.rag_queries,
            "failed_answers": self.failed_answers,
            "answer_success_rate": round(
                1 - (self.failed_answers / self.rag_queries), 3
            )
            if self.rag_queries
            else 1.0,
            "total_tokens": self.total_tokens,
            "latency_ms_p50": pct(50),
            "latency_ms_p95": pct(95),
            "sample_size": len(lat_sorted),
        }


metrics = Metrics()
