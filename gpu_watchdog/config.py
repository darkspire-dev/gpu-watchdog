from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class DetectorThresholds:
    eviction_thrash_count: int = 4
    eviction_thrash_window_s: int = 900
    crash_loop_count: int = 3
    crash_loop_window_s: int = 600
    thundering_herd_count: int = 2
    thundering_herd_window_s: int = 30
    vram_pressure_pct: float = 95.0
    vram_pressure_sustained_s: int = 120
    keep_alive_baseline_s: int = 0  # 0 = disabled; set to configured OLLAMA_KEEP_ALIVE in seconds
    keep_alive_shortfall_pct: float = 50.0  # flag if actual lifetime < this % of baseline


@dataclass
class AlertConfig:
    discord_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    generic_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    cooldown_s: int = 1800  # don't repeat the same alert type more than once per cooldown


@dataclass
class Config:
    ollama_url: str = "http://localhost:11434"
    service_name: str | None = "ollama"  # systemd unit for log tailing, or None to skip
    docker_container: str | None = None  # alternative to service_name
    log_file: str | None = None  # alternative to both of the above
    poll_interval_s: int = 15
    gpu_index: int | str = "all"  # "all" or a specific nvidia-smi index
    license_key: str | None = None
    thresholds: DetectorThresholds = field(default_factory=DetectorThresholds)
    alerts: AlertConfig = field(default_factory=AlertConfig)

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path) as f:
            raw = yaml.safe_load(f) or {}

        thresholds = DetectorThresholds(**raw.get("thresholds", {}))
        alerts = AlertConfig(**raw.get("alerts", {}))

        known = {"thresholds", "alerts"}
        top = {k: v for k, v in raw.items() if k not in known}
        cfg = cls(thresholds=thresholds, alerts=alerts, **top)

        # env var overrides for secrets, so a license/webhook doesn't have to live in the yaml
        cfg.alerts.discord_webhook_url = os.environ.get(
            "GPUWATCHDOG_DISCORD_WEBHOOK", cfg.alerts.discord_webhook_url
        )
        cfg.alerts.slack_webhook_url = os.environ.get(
            "GPUWATCHDOG_SLACK_WEBHOOK", cfg.alerts.slack_webhook_url
        )
        cfg.license_key = os.environ.get("GPUWATCHDOG_LICENSE_KEY", cfg.license_key)
        return cfg
