# Home Internet SLO Monitor — Local Project (DevOps + AIOps lite)

**One‑liner:** Continuously measure latency/jitter/throughput, detect anomalies, and auto‑open a local “ticket” with plots and an ISP‑ready report. 100% local (no cloud).

**Why it signals:** SLOs + anomaly detection + incident automation, entirely on your laptop.

## Acceptance Criteria
- Anomaly PR‑AUC ≥ **0.85** on injected degradations
- SLO alert when **p95 latency > 70 ms for 5 min** (continuous breach)
- Ticket includes **time window + plots + raw metrics sample**
- Deliverables: `scripts/simulate_degradation.sh`, Grafana JSON dashboard, weekly PDF/HTML summary

## Quickstart
1. **Prereqs:** Docker + Docker Compose (or Podman), Python 3.11.
2. Copy env: `cp .env.example .env` (adjust hosts if needed).
3. Start stack: `make up` → Prometheus (**9090**), Grafana (**3000**), Loki (**3100**), API (**8000**).
4. Open Grafana: http://localhost:3000 (dashboard auto‑provisioned under **SLO Monitor**).
5. Inject degradation:
- Linux: `bash scripts/simulate_degradation.sh linux start` (uses `tc netem`).
- macOS: `bash scripts/simulate_degradation.sh mac start` (flag‑file fallback).
6. Watch p95 breach → Alertmanager → `/alert` webhook → ticket JSON under `tickets/` + PNG plots under `reports/`.
7. Weekly report: `python scripts/make_report.py --week $(date +%G-W%V)` → `reports/week-XXXX.html` & PDF.

> **Note (macOS):** `tc netem` isn’t available natively. The script falls back to App Delay mode via `app/.degrade.flag` which injects latency/loss in the probe.

## SLO Spec
- **Availability:** ≥ 99% over a 30‑min demo run
- **Latency:** p95 < 70 ms (5‑min rolling, breach creates alert)
- **Data Freshness:** Probe interval 30 s
- **MTTD:** < 2 min for injected degradation
- **MTTR (ack):** Ticket created within 60 s of sustained breach

## Troubleshooting
- **Loki empty logs:** Ensure Promtail config uses `__path__: /var/log/app/*.log` and that `app/app.log` exists (the app writes JSON lines). The `./app` folder is mounted into Promtail as `/var/log/app`.
- **Grafana not reachable:** Confirm Grafana is mapped to `3000:3000` and open http://localhost:3000.
- **No alerts:** Check Prometheus `Targets` page (http://localhost:9090/targets) and Alertmanager (http://localhost:9093).
