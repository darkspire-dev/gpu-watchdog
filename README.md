# GPU Watchdog

A crash-loop and eviction-thrashing watchdog for self-hosted LLM servers (Ollama today,
vLLM/llama.cpp planned). It watches the things generic GPU monitoring tools don't:

- **Eviction thrashing** — a model getting reloaded over and over because it's fighting
  another model for VRAM or its `keep_alive` isn't sticking.
- **Thundering herd** — multiple models cold-loading at once, which competes for
  disk/GPU bandwidth and makes an already-loaded server look hung.
- **keep_alive shortfall** *(pro)* — a model evicted far sooner than your configured
  `OLLAMA_KEEP_ALIVE` would predict, usually because a client request is overriding it.
- **OOM crash loops** — repeated CUDA OOM errors or service restarts in a short window.
- **Sustained VRAM pressure** — memory pinned near the ceiling for longer than a
  configurable grace period.

Built from a real incident: a multi-GPU Ollama box that kept crash-looping because of a
`MAX_LOADED_MODELS`/`KEEP_ALIVE` misconfiguration, made worse by scripts that hardcoded
`keep_alive:-1` on their own requests and silently defeated the server's policy. Nothing
generic catches that pattern — this does.

## Install

```
pip install -r requirements.txt
cp config.example.yaml config.yaml   # edit: ollama_url, service_name, alert webhook(s)
python -m gpu_watchdog --config config.yaml
```

Runs as a long-lived process — wrap it in a systemd unit or `screen`/`tmux` for
production use.

## Free vs. licensed

Free tier: all core detectors (thrashing, thundering herd, crash-loop, VRAM pressure),
one alert channel of your choice.

A license key (`license_key` in config.yaml, or `GPUWATCHDOG_LICENSE_KEY` env var)
unlocks: multiple simultaneous alert channels (Discord + Slack + email/webhook at once)
and the keep_alive-shortfall detector.

## Config

See `config.example.yaml` — every threshold (thrash count/window, crash-loop
count/window, VRAM pressure %, etc.) is tunable per-deployment.
