# Home Internet SLO Monitor — Local Project (DevOps + AIOps lite)

One‑liner: Continuously measure latency/jitter/throughput, detect anomalies, alert, and auto‑open a local “ticket” with plots and an ISP‑ready report. 100% local (no cloud).

Why it’s interesting: SLOs + anomaly detection + incident automation, entirely on your laptop.

## What’s included
- FastAPI app with `/metrics`, `/alert`, and a simple UI at `/ui`
- Prometheus + rules (p95 SLO, anomaly score)
- Alertmanager → webhook to `/alert`
- Grafana dashboards + alert rules (p95 threshold) with email notifications
- Loki + Promtail for JSON log ingestion
- Ticket + report generation (PNG plots and weekly HTML/PDF)

## Quickstart
1. Prereqs: Docker + Docker Compose (or Podman), Python 3.11 (for local scripts only).
2. Environment: `cp .env.example .env` and adjust if needed.
3. Start: `make up` (or `docker compose up -d --build`)
   - App/API http://localhost:8000
   - UI http://localhost:8000/ui
   - Prometheus http://localhost:9090
   - Grafana http://localhost:3000
   - Alertmanager http://localhost:9093
   - Loki http://localhost:3100/ready (Loki has no UI; use Grafana Explore)

### Email alerts (Grafana)
Grafana is provisioned to send email for alerts. Configure SMTP in `.env` then restart Grafana.

Required `.env` keys (examples for Yahoo):
```
SMTP_HOST=smtp.mail.yahoo.com:587
SMTP_USER=your_email@yahoo.com
SMTP_PASSWORD=<Yahoo App Password>
SMTP_FROM_ADDRESS=your_email@yahoo.com
SMTP_FROM_NAME=Home Internet SLO Monitor
SMTP_STARTTLS_POLICY=MandatoryStartTLS
```

Yahoo requires enabling 2‑step verification and generating an “App password” in the Yahoo Security page. Paste that app password into `SMTP_PASSWORD`, then:
```
docker compose up -d grafana
```
You can send a test from Grafana → Alerting → Contact points → Test.

### Dashboards and UI
- Local UI: http://localhost:8000/ui
  - Service health (App, Prometheus, Grafana, Alertmanager, Loki)
  - Latest probe sample (p95, jitter, loss, throughput, anomaly)
  - Ticket count and recent ticket
  - Quick links + embedded Grafana
- Grafana folder “SLO Monitor” → “Home Internet SLO Monitor” dashboard
- Logs: Grafana → Explore → Loki → query `{job="app"}`

### Alerts
- Prometheus (Alertmanager → webhook `/alert`):
  - HighP95Latency: `histogram_quantile(0.95, …) > 0.07` for 5m
  - HighAnomalyScore: `avg_over_time(app_anomaly_score[5m]) > 0.65` for 2m
- Grafana alert (email + webhook):
  - High p95 latency (same threshold, for 5m)

Tickets are written to `tickets/` with PNG plots under `reports/`.

### Simulate a degradation
- Linux: `bash scripts/simulate_degradation.sh linux start` (uses `tc netem`)
- macOS: `bash scripts/simulate_degradation.sh mac start` (flag file fallback → introduces latency in probes)

Stop: replace `start` with `stop`.

### Weekly report
```
python scripts/make_report.py --week $(date +%G-W%V)
# outputs: reports/week-<WEEK>.html and a minimal PDF
```

## SLO Spec
- Availability ≥ 99% over a 30‑min demo run
- Latency p95 < 70 ms (5‑min rolling, breach creates alert)
- Data Freshness: probe interval 30 s (configurable)
- MTTD < 2 min for injected degradation
- MTTR (ack): Ticket created within 60 s of sustained breach

## Operations
- Start stack: `make up`
- Rebuild app only: `docker compose build app && docker compose up -d app`
- View logs: `docker compose logs -f app` (or use Grafana Explore → Loki)
- Health endpoints:
  - App: `GET http://localhost:8000/healthz`
  - Prometheus: `GET http://localhost:9090/-/ready`
  - Grafana: `GET http://localhost:3000/api/health`
  - Alertmanager: `GET http://localhost:9093/api/v2/status`
  - Loki: `GET http://localhost:3100/ready`

## Notes & Troubleshooting
- Loki 404 at `/`: expected — use Grafana Explore to view logs.
- If Grafana dashboard iframe is blank in `/ui`, it may be a browser blocking third‑party cookies; open Grafana in a new tab.
- If email doesn’t send, verify SMTP_* in `.env`, use your provider’s app password, and check `docker compose logs -f grafana`.
