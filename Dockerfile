FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/darkspire-dev/gpu-watchdog"
LABEL org.opencontainers.image.url="https://llm.lab.darkspire.net"
LABEL org.opencontainers.image.homepage="https://llm.lab.darkspire.net"
LABEL org.opencontainers.image.description="Crash-loop / eviction-thrashing / thundering-herd watchdog for self-hosted LLM servers (Ollama/vLLM/llama.cpp)"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gpu_watchdog ./gpu_watchdog
COPY config.example.yaml .

# nvidia-smi comes from the host via nvidia-container-toolkit (--gpus flag),
# not installed in-image.
ENTRYPOINT ["python", "-m", "gpu_watchdog"]
CMD ["--config", "config.yaml"]
