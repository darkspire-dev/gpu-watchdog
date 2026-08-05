# Decision 001: GPU Watchdog as the Aug 2026 revenue sprint bet

**Date:** 2026-08-05
**Context:** Rob asked for a truly niche, non-overlapping, fully-autonomous path to
$3000-5000 by 2026-08-31 (20 days). Prior brainstorm (50 broad ideas) was rejected as
overlapping existing projects (Whop, trading systems, YouTube). Gumroad ruled out —
its API is read-only, incompatible with "fully autonomous."

**Decision:** Build and sell a one-time-license daemon that watches self-hosted LLM
servers (Ollama first) for crash-loops, VRAM eviction thrashing, and thundering-herd
cold-load storms — problems generic GPU monitoring tools don't target.

**Why this and not another idea:**
- Non-overlapping: nothing else in the project portfolio touches self-hosted LLM
  infrastructure tooling.
- Credible without prior audience: the launch story is Rob's own RAVEN-GPT incident
  (VRAM eviction thrashing + `keep_alive:-1` client override bug, see
  `/home/administrator/watchdogs/raven_gpt_watchdog.py` and project memory
  `project_raven_gpt.md`) — a real, specific, technically-verifiable problem, not a
  generic pitch.
- r/LocalLLaMA and r/homelab are large, technical, high-intent audiences already
  discussing this exact pain.
- Fully automatable end to end: Stripe Payment Link (API-created) + n8n webhook
  fulfillment, no manual per-sale steps.

**Pricing/licensing model:** Open-core (MIT) — free tier covers all core detectors with
one alert channel; a purchased license key (HMAC-signed, offline-validated, no
phone-home server required) unlocks multi-channel alerting and the keep_alive-shortfall
detector. Chose offline HMAC over a hosted license server to avoid building/maintaining
backend infra during a 20-day sprint — accepted tradeoff: a determined user could patch
around the gate, judged not worth engineering against at this price point ($29-49).

**Payment processor:** Stripe over Square (Rob has accounts with both) — Square's risk
models skew toward physical/in-person commerce and are more likely to flag/hold payouts
on a new pure-digital-goods pattern, an asymmetric risk on a hard deadline. See memory
`feedback_square_vs_stripe` equivalent conversation, 2026-08-05.

**Status:** MVP built and unit-tested same day (detectors validated against synthetic
data + a real bug found/fixed in `EvictionThrashingDetector` during testing: a
`list | set` TypeError). `ollama_client` parsing validated against live RAVEN-GPT
(172.16.0.175) — correctly parses real `/api/ps` responses including the
9-fractional-digit timestamp format Ollama emits. Not yet deployed as a running daemon;
not yet packaged for Stripe/launch.
