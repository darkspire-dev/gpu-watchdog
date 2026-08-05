from __future__ import annotations

import socket
import time

from . import gpu_metrics, ollama_client
from .alerts import AlertDispatcher
from .config import Config
from .detectors import (
    Alert,
    EvictionThrashingDetector,
    KeepAliveShortfallDetector,
    OomCrashLoopDetector,
    ThunderingHerdDetector,
    VramPressureDetector,
)
from .license import is_pro
from .log_tail import make_tailer


def _log(msg: str) -> None:
    print(f"[gpu-watchdog] {msg}", flush=True)


def _enforce_free_tier(cfg: Config) -> None:
    """Free tier: one alert channel, no keep_alive-shortfall detector (needs a
    hand-tuned baseline, treated as a pro/consulting-tier feature)."""
    if is_pro(cfg.license_key):
        return
    channels = [
        ("discord_webhook_url", cfg.alerts.discord_webhook_url),
        ("slack_webhook_url", cfg.alerts.slack_webhook_url),
        ("generic_webhook_url", cfg.alerts.generic_webhook_url),
    ]
    configured = [name for name, val in channels if val]
    if len(configured) > 1:
        keep = configured[0]
        _log(f"Free tier: only one alert channel allowed, keeping '{keep}', "
             f"disabling {configured[1:]}. A license key unlocks all channels.")
        for name, _ in channels:
            if name != keep:
                setattr(cfg.alerts, name, None)
        cfg.alerts.smtp_host = None
    if cfg.thresholds.keep_alive_baseline_s:
        _log("Free tier: keep_alive-shortfall detection is a pro feature, disabling. "
             "A license key unlocks it.")
        cfg.thresholds.keep_alive_baseline_s = 0


def run(cfg: Config) -> None:
    _enforce_free_tier(cfg)

    source_label = socket.gethostname()
    dispatcher = AlertDispatcher(cfg.alerts, source_label)

    thrash_detector = EvictionThrashingDetector(cfg.thresholds)
    herd_detector = ThunderingHerdDetector(cfg.thresholds)
    keepalive_detector = KeepAliveShortfallDetector(cfg.thresholds)
    crash_detector = OomCrashLoopDetector(cfg.thresholds)
    vram_detector = VramPressureDetector(cfg.thresholds)

    tailer = make_tailer(cfg.service_name, cfg.docker_container, cfg.log_file)
    if tailer is None:
        _log("No log source configured (service_name/docker_container/log_file all "
             "unset) -- crash-loop detection from logs is disabled, GPU/ollama polling "
             "still active.")

    was_reachable = True
    _log(f"Starting on {source_label}, polling {cfg.ollama_url} every {cfg.poll_interval_s}s "
         f"(tier: {'pro' if is_pro(cfg.license_key) else 'free'})")

    while True:
        loop_start = time.monotonic()
        all_alerts: list[Alert] = []

        models = ollama_client.poll_loaded_models(cfg.ollama_url)
        if models is None:
            if was_reachable:
                all_alerts.append(Alert(
                    severity="critical", title="Ollama unreachable",
                    body=f"Could not reach {cfg.ollama_url}/api/ps.", key="unreachable",
                ))
            was_reachable = False
        else:
            if not was_reachable:
                all_alerts.append(Alert(
                    severity="warning", title="Ollama back online",
                    body="Recovered after being unreachable.", key="recovered",
                ))
            was_reachable = True
            all_alerts += thrash_detector.update(models)
            all_alerts += herd_detector.update(models)
            all_alerts += keepalive_detector.update(models)

        samples = gpu_metrics.poll_gpus()
        all_alerts += vram_detector.update(samples)

        if tailer is not None:
            for line in tailer.drain():
                all_alerts += crash_detector.feed_line(line)

        if all_alerts:
            for a in all_alerts:
                _log(f"{a.severity.upper()} {a.title}: {a.body}")
            dispatcher.dispatch(all_alerts)

        elapsed = time.monotonic() - loop_start
        time.sleep(max(0.0, cfg.poll_interval_s - elapsed))
