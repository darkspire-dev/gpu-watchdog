from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class GpuSample:
    index: int
    name: str
    mem_used_mib: float
    mem_total_mib: float
    utilization_pct: float
    temperature_c: float

    @property
    def mem_pct(self) -> float:
        return (self.mem_used_mib / self.mem_total_mib * 100) if self.mem_total_mib else 0.0


QUERY_FIELDS = "index,name,memory.used,memory.total,utilization.gpu,temperature.gpu"


def poll_gpus() -> list[GpuSample]:
    """Poll nvidia-smi for current GPU state. Returns [] if nvidia-smi is unavailable
    (e.g. dry-run on a non-GPU box) rather than raising, so the rest of the daemon can
    keep running the log/ollama-based detectors."""
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={QUERY_FIELDS}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    samples = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 6:
            continue
        idx, name, mem_used, mem_total, util, temp = parts
        try:
            samples.append(GpuSample(
                index=int(idx), name=name,
                mem_used_mib=float(mem_used), mem_total_mib=float(mem_total),
                utilization_pct=float(util), temperature_c=float(temp),
            ))
        except ValueError:
            continue
    return samples
