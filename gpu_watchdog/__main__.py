from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import Config
from .daemon import run


def main() -> None:
    parser = argparse.ArgumentParser(prog="gpu-watchdog",
                                      description="Crash-loop and eviction-thrashing watchdog for self-hosted LLM servers (Ollama/vLLM/llama.cpp).")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--version", action="version", version=f"gpu-watchdog {__version__}")
    args = parser.parse_args()

    try:
        cfg = Config.load(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}\n"
              f"Copy config.example.yaml to config.yaml and edit it first.", file=sys.stderr)
        sys.exit(1)

    try:
        run(cfg)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
