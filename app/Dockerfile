FROM python:3.11-slim
WORKDIR /app

# Add ping + iperf3 inside the container
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping iperf3 \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

# Ensure headless plotting works reliably
ENV MPLBACKEND=Agg

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
