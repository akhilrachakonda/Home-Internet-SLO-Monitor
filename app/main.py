from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime, timedelta
import threading, time, os, json, pathlib
from config import CFG
from probes import run_ping, run_iperf
from anomaly import SlidingIForest
from tickets import TicketSink
from plotting import save_time_series

LOG_PATH = pathlib.Path(__file__).resolve().parent / "app.log"

app = FastAPI()
reg = CollectorRegistry()
REQS = Counter("app_requests_total", "requests", registry=reg)
LAT = Histogram("app_request_latency", "latency", registry=reg)
JITTER = Gauge("app_jitter_ms", "jitter", registry=reg)
LOSS = Gauge("app_packet_loss_pct", "loss", registry=reg)
THR = Gauge("app_throughput_mbps", "throughput", registry=reg)
ANOM = Gauge("app_anomaly_score", "score", registry=reg)
TICK = Counter("app_ticket_created_total", "tickets", registry=reg)

points = []  # (ts, p95_s, jitter_ms, loss_pct, mbps)
iforest = SlidingIForest(window=CFG["ANOMALY_WINDOW"])
tickets = TicketSink(CFG["TICKETS_DIR"])

BREACH_WINDOW = []  # times of breach samples for SLO logic

@app.get("/healthz")
def health(): return {"ok": True}

@app.get("/metrics")
def metrics(): return Response(generate_latest(reg), media_type=CONTENT_TYPE_LATEST)

@app.post("/alert")
async def alert(req: Request):
    payload = await req.json()
    now = datetime.utcnow(); since = now - timedelta(minutes=15)
    ts, p95s, jit, los, mbps = [], [], [], [], []
    for (t, p95, j, l, m) in points:
        if t >= since:
            ts.append(t)
            p95s.append(p95)
            jit.append(j)
            los.append(l)
            mbps.append(m)
    plots = []
    for y, name in [(p95s, "p95_s"), (jit, "jitter_ms"), (los, "loss_pct"), (mbps, "throughput_mbps")]:
        out = f"{CFG['REPORTS_DIR']}/alert-{now:%Y%m%d-%H%M%S}-{name}.png"
        save_time_series(ts, y, name, out)
        plots.append(out)
    path = tickets.create(
        title="SLO Breach: High p95 latency",
        window={"from": since.isoformat(), "to": now.isoformat()},
        summary=payload,
        plots=plots)
    TICK.inc()
    return {"ticket": path}

def log_json(obj):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(obj) + "\n")
    except Exception:
        pass

def probe_loop():
    while True:
        t0 = time.time()
        degrade_flag = os.path.exists(os.path.join(os.path.dirname(__file__), ".degrade.flag"))
        ping = run_ping(CFG["TARGET_HOST"], CFG["PING_COUNT"], degrade_flag)
        iperf = run_iperf(CFG["IPERF_HOST"]) if (int(time.time())//60) % 5 == 0 else {"throughput_mbps": 0.0}
        ts = datetime.utcnow()
        p95_s, jitter_ms, loss_pct = ping["p95_s"], ping["jitter_ms"], ping["loss_pct"]
        mbps = iperf["throughput_mbps"]
        points.append((ts, p95_s, jitter_ms, loss_pct, mbps))
        if len(points) > 2000: points.pop(0)
        # metrics
        JITTER.set(jitter_ms)
        LOSS.set(loss_pct)
        THR.set(mbps)
        LAT.observe(p95_s)
        score = iforest.add(p95_s, jitter_ms, loss_pct, mbps)
        ANOM.set(score)
        # log for Loki
        log_json({"ts": ts.isoformat(), "p95_s": p95_s, "jitter_ms": jitter_ms, "loss_pct": loss_pct, "throughput_mbps": mbps, "anomaly": score})
        # SLO breach tracking
        threshold = float(os.getenv("ALERT_LATENCY_P95_MS", "70")) / 1000.0
        now = datetime.utcnow()
        if p95_s > threshold:
            BREACH_WINDOW.append(now)
            cutoff = now - timedelta(minutes=int(os.getenv("ALERT_BREACH_MINUTES", "5")))
            BREACH_WINDOW[:] = [t for t in BREACH_WINDOW if t >= cutoff]
            if (BREACH_WINDOW and (BREACH_WINDOW[0] <= cutoff) and (len(BREACH_WINDOW) >= int(os.getenv("PING_COUNT","10")))):
                import requests
                try:
                    requests.post("http://localhost:8000/alert", json={"reason":"local_slo_breach"}, timeout=3)
                except Exception:
                    pass
                BREACH_WINDOW.clear()
        time.sleep(max(1, CFG["PROBE_INTERVAL_SEC"] - (time.time()-t0)))

import threading
threading.Thread(target=probe_loop, daemon=True).start()
