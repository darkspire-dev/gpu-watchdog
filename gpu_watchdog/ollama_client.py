from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests


@dataclass
class LoadedModel:
    name: str
    size_vram_bytes: int
    expires_at: datetime | None


def _parse_expiry(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        # Ollama emits e.g. "2026-08-05T02:29:52.037014967-07:00" -- Python's fromisoformat
        # chokes on 9-digit fractional seconds, so truncate to microsecond precision.
        if "." in raw:
            head, rest = raw.split(".", 1)
            frac, _, tz = rest.partition(next(c for c in rest if c in "+-Z"))
            raw = f"{head}.{frac[:6]}{rest[len(frac):]}"
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def poll_loaded_models(ollama_url: str, timeout: float = 8.0) -> list[LoadedModel] | None:
    """Returns None (not []) on connection failure, so callers can distinguish
    'ollama unreachable' from 'ollama reachable, nothing loaded'."""
    try:
        r = requests.get(f"{ollama_url}/api/ps", timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None

    out = []
    for m in data.get("models", []):
        out.append(LoadedModel(
            name=m.get("name", "unknown"),
            size_vram_bytes=int(m.get("size_vram", 0)),
            expires_at=_parse_expiry(m.get("expires_at")),
        ))
    return out


def ollama_reachable(ollama_url: str, timeout: float = 5.0) -> bool:
    try:
        r = requests.get(f"{ollama_url}/api/version", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
