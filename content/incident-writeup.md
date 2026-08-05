# Why our Ollama box kept crash-looping (and what actually fixed it)

We run a multi-GPU box (three RTX 3060s and an old 1080) serving a couple of Ollama
models for internal tooling. It started crash-looping under completely normal traffic —
no spikes, no unusual load. `nvidia-smi` looked fine every time we checked. Dashboards
looked fine. Nothing caught it until someone went through the raw logs by hand.

The actual cause was two compounding things:

1. The server's `OLLAMA_MAX_LOADED_MODELS` and `OLLAMA_KEEP_ALIVE` were misconfigured,
   so models were getting evicted far more aggressively than intended.
2. On top of that, three separate scripts calling the server were hardcoding
   `keep_alive: -1` (or `0`) on their own requests — silently overriding whatever the
   server was configured to do, on every single call. Nobody remembered these scripts
   were still running.

So the box wasn't actually unstable. It was being told to do something impossible,
repeatedly, by code that had been forgotten about. Once we found it, the fix was
trivial — the hard part was finding it, because none of the generic monitoring we had
(GPU utilization, memory graphs, uptime checks) surfaces "a client keeps overriding your
keep_alive policy" as a signal. It just looks like unexplained instability.

That gap is specific enough that nothing generic catches it, so we ended up writing a
small watchdog for exactly this pattern: eviction thrashing (a model getting reloaded
over and over), thundering herd (multiple models cold-loading at once, which is brutal
right after a reboot), OOM crash loops, sustained VRAM pressure, and the keep_alive
mismatch itself. It watches `/api/ps` and the server logs and alerts to
Discord/Slack/email when it sees the pattern.

Made it free/open-core since the failure mode is common enough that it seemed worth
sharing rather than sitting on it.
