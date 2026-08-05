from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .config import DetectorThresholds
from .gpu_metrics import GpuSample
from .ollama_client import LoadedModel

OOM_PATTERNS = [
    re.compile(r"CUDA error", re.I),
    re.compile(r"out of memory", re.I),
    re.compile(r"CUDA_ERROR_OUT_OF_MEMORY", re.I),
    re.compile(r"ggml_cuda_.*alloc.*fail", re.I),
    re.compile(r"failed to allocate", re.I),
    re.compile(r"panic:", re.I),
]
SERVICE_START_PATTERN = re.compile(r"Started .*Ollama", re.I)


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Alert:
    severity: str  # "warning" | "critical"
    title: str
    body: str
    key: str  # dedup/cooldown key


class EvictionThrashingDetector:
    """A model that keeps disappearing and reappearing from /api/ps in a short window is
    fighting another model for VRAM/keep_alive slots -- the exact RAVEN-GPT symptom."""

    def __init__(self, thresholds: DetectorThresholds):
        self.t = thresholds
        self._present_last: dict[str, bool] = {}
        self._reload_events: dict[str, deque] = defaultdict(deque)

    def update(self, models: list[LoadedModel]) -> list[Alert]:
        alerts = []
        present_now = {m.name for m in models}
        for name in present_now:
            was_present = self._present_last.get(name, False)
            if was_present is False and name in self._present_last:
                # was previously seen, dropped out, now back -- a reload
                self._reload_events[name].append(now())

        # drop anything not seen this poll (mark as absent) but keep history
        for name in set(self._present_last.keys()) | present_now:
            self._present_last[name] = name in present_now

        window = timedelta(seconds=self.t.eviction_thrash_window_s)
        for name, events in self._reload_events.items():
            while events and events[0] < now() - window:
                events.popleft()
            if len(events) >= self.t.eviction_thrash_count:
                alerts.append(Alert(
                    severity="warning",
                    title=f"Eviction thrashing: {name}",
                    body=(f"`{name}` has been reloaded {len(events)} times in the last "
                          f"{self.t.eviction_thrash_window_s // 60} min. Likely VRAM "
                          f"pressure from too many concurrent models, or a keep_alive "
                          f"setting that isn't sticking."),
                    key=f"thrash:{name}",
                ))
                events.clear()
        return alerts


class ThunderingHerdDetector:
    """Multiple models entering a cold-load state within a short window compete for
    disk/GPU bandwidth and make an already-loaded server look unresponsive -- this is
    what made RAVEN-GPT fragile right after a reboot."""

    def __init__(self, thresholds: DetectorThresholds):
        self.t = thresholds
        self._known_names: set[str] = set()
        self._load_events: deque = deque()
        self._primed = False

    def update(self, models: list[LoadedModel]) -> list[Alert]:
        current = {m.name for m in models}
        if not self._primed:
            # Models already loaded when the daemon starts aren't a "cold load event" --
            # without this, every already-warm model looks like it just started loading
            # simultaneously on the very first poll (seen live against RAVEN-GPT: startup
            # falsely flagged mistral+qwen3.6, both hours-old, as a thundering herd).
            self._known_names |= current
            self._primed = True
            return []
        new_names = current - self._known_names
        self._known_names |= current
        ts = now()
        for _ in new_names:
            self._load_events.append(ts)

        window = timedelta(seconds=self.t.thundering_herd_window_s)
        while self._load_events and self._load_events[0] < ts - window:
            self._load_events.popleft()

        if len(self._load_events) >= self.t.thundering_herd_count and new_names:
            self._load_events.clear()
            return [Alert(
                severity="warning",
                title="Thundering herd: concurrent cold model loads",
                body=(f"{len(new_names)} model(s) started loading within "
                      f"{self.t.thundering_herd_window_s}s of each other "
                      f"({', '.join(sorted(new_names))}). Concurrent cold loads compete "
                      f"for disk/GPU bandwidth and can make the server look hung. Consider "
                      f"pre-warming sequentially instead of letting retries pile up."),
                key="thundering_herd",
            )]
        return []


class KeepAliveShortfallDetector:
    """If a model gets evicted much sooner than the server's configured keep_alive would
    predict, something (usually a client hardcoding keep_alive:0 or a low value on its
    own requests) is overriding server policy -- the exact bug found on RAVEN-GPT
    (scripts hardcoding keep_alive:-1)."""

    def __init__(self, thresholds: DetectorThresholds):
        self.t = thresholds
        self._first_seen: dict[str, datetime] = {}
        self._was_present: set[str] = set()

    def update(self, models: list[LoadedModel]) -> list[Alert]:
        if not self.t.keep_alive_baseline_s:
            return []
        alerts = []
        current = {m.name for m in models}
        ts = now()
        for m in models:
            self._first_seen.setdefault(m.name, ts)

        evicted = self._was_present - current
        for name in evicted:
            first = self._first_seen.pop(name, None)
            if first is None:
                continue
            lifetime_s = (ts - first).total_seconds()
            shortfall_pct = (lifetime_s / self.t.keep_alive_baseline_s) * 100
            if shortfall_pct < self.t.keep_alive_shortfall_pct:
                alerts.append(Alert(
                    severity="warning",
                    title=f"keep_alive shortfall: {name}",
                    body=(f"`{name}` was evicted after only {lifetime_s:.0f}s, but the "
                          f"configured keep_alive baseline is "
                          f"{self.t.keep_alive_baseline_s}s ({shortfall_pct:.0f}% of "
                          f"expected). Check for a client request overriding keep_alive "
                          f"on this model."),
                    key=f"keepalive:{name}",
                ))
        self._was_present = current
        return alerts


class OomCrashLoopDetector:
    def __init__(self, thresholds: DetectorThresholds):
        self.t = thresholds
        self._oom_events: deque = deque()
        self._restart_events: deque = deque()

    def feed_line(self, line: str) -> list[Alert]:
        alerts = []
        ts = now()
        if any(p.search(line) for p in OOM_PATTERNS):
            self._oom_events.append(ts)
        if SERVICE_START_PATTERN.search(line):
            self._restart_events.append(ts)

        window = timedelta(seconds=self.t.crash_loop_window_s)
        for dq, label, alert_key in (
            (self._oom_events, "OOM error(s)", "oom"),
            (self._restart_events, "service restart(s)", "crash_loop"),
        ):
            while dq and dq[0] < ts - window:
                dq.popleft()
            if len(dq) >= self.t.crash_loop_count:
                alerts.append(Alert(
                    severity="critical",
                    title=f"Crash loop detected ({label})",
                    body=(f"{len(dq)} {label} in the last "
                          f"{self.t.crash_loop_window_s // 60} min. This looks like a "
                          f"crash loop, not a one-off failure."),
                    key=alert_key,
                ))
                dq.clear()
        return alerts


class VramPressureDetector:
    def __init__(self, thresholds: DetectorThresholds):
        self.t = thresholds
        self._pressure_since: dict[int, datetime] = {}

    def update(self, samples: list[GpuSample]) -> list[Alert]:
        alerts = []
        ts = now()
        seen = set()
        for s in samples:
            seen.add(s.index)
            if s.mem_pct >= self.t.vram_pressure_pct:
                start = self._pressure_since.setdefault(s.index, ts)
                sustained = (ts - start).total_seconds()
                if sustained >= self.t.vram_pressure_sustained_s:
                    alerts.append(Alert(
                        severity="warning",
                        title=f"Sustained VRAM pressure: GPU {s.index} ({s.name})",
                        body=(f"{s.mem_pct:.1f}% VRAM used for {sustained:.0f}s "
                              f"({s.mem_used_mib:.0f}/{s.mem_total_mib:.0f} MiB). Eviction "
                              f"thrashing is likely under this load."),
                        key=f"vram_pressure:{s.index}",
                    ))
                    self._pressure_since[s.index] = ts  # re-cooldown locally too
            else:
                self._pressure_since.pop(s.index, None)
        for idx in list(self._pressure_since):
            if idx not in seen:
                self._pressure_since.pop(idx, None)
        return alerts
