from __future__ import annotations

import subprocess
from collections.abc import Iterator


class LogTailer:
    """Wraps a subprocess that streams new log lines (journalctl -f / docker logs -f /
    tail -F), exposing a non-blocking drain() so the main poll loop never stalls waiting
    on log output that might not come."""

    def __init__(self, cmd: list[str]):
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1,
        )
        import os
        import fcntl
        fd = self._proc.stdout.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def drain(self) -> Iterator[str]:
        while True:
            try:
                line = self._proc.stdout.readline()
            except (BlockingIOError, TypeError):
                return
            if not line:
                return
            yield line.rstrip("\n")

    def close(self):
        self._proc.terminate()


def make_tailer(service_name: str | None, docker_container: str | None,
                 log_file: str | None) -> LogTailer | None:
    if service_name:
        return LogTailer(["journalctl", "-u", service_name, "-f", "-n", "0", "--no-pager"])
    if docker_container:
        return LogTailer(["docker", "logs", "-f", "--tail", "0", docker_container])
    if log_file:
        return LogTailer(["tail", "-F", "-n", "0", log_file])
    return None
