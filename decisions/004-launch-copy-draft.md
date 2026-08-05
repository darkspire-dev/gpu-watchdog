# Decision 004: Launch copy (draft, not yet posted)

**Date:** 2026-08-05
**Status:** DRAFT — blocked on a public code-hosting link (see below), not yet posted
anywhere. Task #6 is otherwise ready to fire the moment that's resolved.

## Why this isn't posted yet

Two problems surfaced while prepping the actual launch:
1. Standing rule ([[feedback_no_lab_urls_public]] in memory): never put a
   `*.lab.darkspire.net` URL in a public Reddit/HN post. The landing page domain I just
   requested is exactly that — fine for internal/staging reference, wrong for the post
   itself.
2. The Gitea instance (`172.16.0.19:3000`) is on an internal RFC1918 IP. Reddit/HN
   readers cannot reach it at all, lab-URL rule or not.

Net: there's no genuinely public link to point the launch post at yet. The fix is a
public GitHub mirror (also the audience-expected place for this exact crowd — r/LocalLLaMA
and HN readers trust GitHub far more than an unknown self-hosted Gitea instance). No
GitHub credentials exist in `/home/administrator/auth` — creating a new public identity
isn't something to invent unilaterally, so this is a real question for Rob, not a thing
to solve alone.

## r/LocalLLaMA

**Title:** I built a watchdog for the crash-loop that took down our own Ollama box —
open-sourced it

**Body:**
> Our multi-GPU Ollama server (3x RTX 3060 + a 1080) kept crash-looping under normal
> traffic. `nvidia-smi` looked fine between crashes. Dashboards looked fine. Took going
> through the logs by hand to find it: `MAX_LOADED_MODELS`/`KEEP_ALIVE` were
> misconfigured on the server, AND three separate scripts were hardcoding
> `keep_alive: -1` on their own requests — silently overriding server policy every
> single call. The box wasn't unstable, it was being told to do something impossible,
> repeatedly, by code nobody remembered was still running.
>
> Built a small watchdog for the pattern since nothing generic catches it:
> - eviction thrashing (a model getting reloaded over and over — VRAM fight or a
>   keep_alive that isn't sticking)
> - thundering herd (multiple models cold-loading at once, usually right after a
>   reboot, competing for disk/GPU bandwidth)
> - OOM crash loops
> - sustained VRAM pressure
> - (paid tier) keep_alive-shortfall detection — catches the exact bug above
>
> Free/open-core, MIT, all 5 detectors work in the free tier — the paid tier
> ($39 one-time) just adds multi-channel alerting and that last detector. Source: https://github.com/darkspire-dev/gpu-watchdog
>
> Happy to answer questions about the detection logic or the original incident.

## r/homelab

**Title:** Watchdog for GPU/LLM servers — catches the failure modes nvidia-smi alone
won't show you

**Body:**
> If you're running Ollama/vLLM/llama.cpp on a homelab GPU box, this might save you a
> 3am page: a small daemon that watches for eviction thrashing, cold-load storms after
> a reboot, OOM crash loops, and sustained VRAM pressure — alerts to Discord/Slack/email.
> Free and open-core (MIT). Built it after our own multi-GPU box kept crash-looping for
> a genuinely dumb reason (details in the post/README). Source + free download: https://github.com/darkspire-dev/gpu-watchdog

## Show HN

**Title:** Show HN: GPU Watchdog – crash-loop and VRAM-thrashing monitor for
self-hosted LLM servers

**First comment (by author):**
> Built this after a real incident: a multi-GPU Ollama box kept crash-looping, and the
> actual cause turned out to be a server misconfig compounded by scripts silently
> overriding `keep_alive` on every request. Nothing generic (nvidia-smi dashboards,
> Prometheus GPU exporters) targets this specific failure pattern, so I wrote something
> that does. Open-core/MIT, all core detectors are free; a $39 one-time license adds
> multi-channel alerting and one extra detector. Feedback on the detection logic
> especially welcome — happy to go into the internals.

## Resolved

Public repo is live at `https://github.com/darkspire-dev/gpu-watchdog` (Rob created the
account, provided a token 2026-08-05). Links above are filled in and real. These three
posts are ready to submit as-is, or edited first — Rob's call before they actually go
out, since posting under the company identity to public forums isn't something to do
without a final look.
