from __future__ import annotations

import smtplib
import time
from email.mime.text import MIMEText

import requests

from .config import AlertConfig
from .detectors import Alert

SEVERITY_EMOJI = {"warning": "\U0001f7e1", "critical": "\U0001f534"}


class AlertDispatcher:
    def __init__(self, cfg: AlertConfig, source_label: str):
        self.cfg = cfg
        self.source_label = source_label
        self._last_sent: dict[str, float] = {}

    def _on_cooldown(self, key: str) -> bool:
        last = self._last_sent.get(key)
        return last is not None and (time.monotonic() - last) < self.cfg.cooldown_s

    def dispatch(self, alerts: list[Alert]) -> None:
        for a in alerts:
            if self._on_cooldown(a.key):
                continue
            self._last_sent[a.key] = time.monotonic()
            self._send(a)

    def _send(self, a: Alert) -> None:
        emoji = SEVERITY_EMOJI.get(a.severity, "⚠️")
        text = f"{emoji} **[{self.source_label}] {a.title}**\n{a.body}"

        if self.cfg.discord_webhook_url:
            self._post_json(self.cfg.discord_webhook_url, {"content": text})
        if self.cfg.slack_webhook_url:
            self._post_json(self.cfg.slack_webhook_url, {"text": text})
        if self.cfg.generic_webhook_url:
            self._post_json(self.cfg.generic_webhook_url, {
                "severity": a.severity, "title": a.title, "body": a.body,
                "source": self.source_label,
            })
        if self.cfg.smtp_host and self.cfg.smtp_to:
            self._send_email(a, text)

    @staticmethod
    def _post_json(url: str, payload: dict) -> None:
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception:
            pass  # alerting must never crash the monitor loop

    def _send_email(self, a: Alert, text: str) -> None:
        try:
            msg = MIMEText(text)
            msg["Subject"] = f"[{self.source_label}] {a.title}"
            msg["From"] = self.cfg.smtp_from or self.cfg.smtp_user or "gpu-watchdog@localhost"
            msg["To"] = self.cfg.smtp_to
            with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port, timeout=15) as s:
                s.starttls()
                if self.cfg.smtp_user:
                    s.login(self.cfg.smtp_user, self.cfg.smtp_password or "")
                s.send_message(msg)
        except Exception:
            pass
