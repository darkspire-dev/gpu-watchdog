from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

# Offline HMAC-signed license keys. This is intentionally NOT hardened DRM -- at this
# price point ($29-49 one-time) the goal is a light honesty gate for the "pro" features
# (multi-node aggregation, >1 alert channel, historical export), not piracy-proofing.
# See decisions/001-why-this-product.md.
_DEFAULT_SECRET = "V9UdJQqnoTayN9HkICdgT1xj-4Rjymkgyzrz7NDpACs"


def _secret() -> bytes:
    return os.environ.get("GPUWATCHDOG_LICENSE_SECRET", _DEFAULT_SECRET).encode()


def issue_license(customer: str, tier: str = "pro") -> str:
    payload = {"customer": customer, "tier": tier, "issued": int(time.time())}
    payload_b = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_secret(), payload_b, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(payload_b).decode().rstrip("=")
        + "."
        + base64.urlsafe_b64encode(sig).decode().rstrip("=")
    )


def _pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def validate_license(key: str | None) -> dict | None:
    """Returns the decoded payload dict if valid, else None. A None/missing key is
    treated as the free tier -- callers should check `is_pro()` rather than assuming
    validate_license truthiness means paid."""
    if not key or "." not in key:
        return None
    try:
        payload_part, sig_part = key.split(".", 1)
        payload_b = base64.urlsafe_b64decode(_pad(payload_part))
        sig = base64.urlsafe_b64decode(_pad(sig_part))
        expected = hmac.new(_secret(), payload_b, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        return json.loads(payload_b)
    except Exception:
        return None


def is_pro(key: str | None) -> bool:
    payload = validate_license(key)
    return bool(payload and payload.get("tier") == "pro")
