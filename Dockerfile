FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gpu_watchdog ./gpu_watchdog
COPY config.example.yaml .

# nvidia-smi comes from the host via nvidia-container-toolkit (--gpus flag),
# not installed in-image.
ENTRYPOINT ["python", "-m", "gpu_watchdog"]
CMD ["--config", "config.yaml"]
