from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from datetime import datetime, timedelta
import time, os, json, pathlib

# Support running as a package (app.*) or as a module (main.py)
try:
    from .config import CFG  # type: ignore
    from .probes import run_ping, run_iperf  # type: ignore
    from .anomaly import SlidingIForest  # type: ignore
    from .tickets import TicketSink  # type: ignore
    from .plotting import save_time_series  # type: ignore
except Exception:  # pragma: no cover
    from config import CFG  # type: ignore
    from probes import run_ping, run_iperf  # type: ignore
    from anomaly import SlidingIForest  # type: ignore
    from tickets import TicketSink  # type: ignore
    from plotting import save_time_series  # type: ignore

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
last_score = 0.0

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
        global last_score
        last_score = score
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


@app.get("/ui", response_class=HTMLResponse)
def ui_page():
    # Lightweight status console with links and embedded Grafana
    return """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\"/>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <title>Home Internet SLO Monitor — UI</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; }
    header { padding: 12px 16px; background: #0f172a; color: #fff; }
    .wrap { padding: 16px; display: grid; grid-template-columns: 1fr; gap: 16px; }
    .cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
    .ok { color: #16a34a; font-weight: 600; }
    .bad { color: #dc2626; font-weight: 600; }
    .links a { margin-right: 12px; }
    iframe { width: 100%; height: 60vh; border: 0; border-top: 1px solid #e5e7eb; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 4px 6px; text-align: left; }
  </style>
  <script>
    async function refresh() {
      try {
        const r = await fetch('/ui/status');
        const s = await r.json();
        const el = (id, v) => document.getElementById(id).textContent = v;
        el('app', s.app.ok ? 'OK' : 'DOWN');
        el('prom', s.prometheus.ok ? 'OK' : 'DOWN');
        el('graf', s.grafana.ok ? 'OK' : 'DOWN');
        el('am', s.alertmanager.ok ? 'OK' : 'DOWN');
        el('loki', s.loki.ok ? 'OK' : 'DOWN');
        el('p95', s.sample.p95_s.toFixed(3)+' s');
        el('jit', s.sample.jitter_ms.toFixed(1)+' ms');
        el('loss', s.sample.loss_pct.toFixed(1)+' %');
        el('thr', s.sample.throughput_mbps.toFixed(1)+' Mbps');
        el('anom', s.sample.anomaly.toFixed(3));
        el('tickets', s.tickets.count + ' total');
        el('last_ticket', s.tickets.last || '—');
      } catch (e) { console.error(e); }
    }
    setInterval(refresh, 5000);
    window.addEventListener('load', refresh);
  </script>
</head>
<body>
  <header>
    <h2>Home Internet SLO Monitor — Control Panel</h2>
  </header>
  <div class=\"wrap\">
    <div class=\"cards\">
      <div class=\"card\"><div>App</div><div id=\"app\" class=\"ok\">…</div></div>
      <div class=\"card\"><div>Prometheus</div><div id=\"prom\" class=\"ok\">…</div></div>
      <div class=\"card\"><div>Grafana</div><div id=\"graf\" class=\"ok\">…</div></div>
      <div class=\"card\"><div>Alertmanager</div><div id=\"am\" class=\"ok\">…</div></div>
      <div class=\"card\"><div>Loki</div><div id=\"loki\" class=\"ok\">…</div></div>
      <div class=\"card\">
        <div>Latest Probe</div>
        <table>
          <tr><th>p95</th><td id=\"p95\">…</td></tr>
          <tr><th>jitter</th><td id=\"jit\">…</td></tr>
          <tr><th>loss</th><td id=\"loss\">…</td></tr>
          <tr><th>throughput</th><td id=\"thr\">…</td></tr>
          <tr><th>anomaly</th><td id=\"anom\">…</td></tr>
        </table>
      </div>
      <div class=\"card\">
        <div>Tickets</div>
        <div id=\"tickets\">…</div>
        <div id=\"last_ticket\" style=\"font-size:12px;color:#475569\"></div>
      </div>
    </div>
    <div class=\"links\">
      <a href=\"http://localhost:3000\" target=\"_blank\">Open Grafana</a>
      <a href=\"http://localhost:9090\" target=\"_blank\">Open Prometheus</a>
      <a href=\"http://localhost:9093\" target=\"_blank\">Open Alertmanager</a>
      <a href=\"http://localhost:3000/explore?left=%5B%22now-6h%22,%22now%22,%22loki%22,%7B%7D%5D\" target=\"_blank\">Open Logs (Grafana Explore)</a>
      <a href=\"/metrics\" target=\"_blank\">App Metrics</a>
    </div>
    <iframe src=\"http://localhost:3000/dashboards\" title=\"Grafana\"></iframe>
  </div>
</body>
</html>
    """


@app.get("/ui/status")
def ui_status():
    import requests
    def ok(url, parse=None):
        try:
            r = requests.get(url, timeout=2)
            r.raise_for_status()
            return True, (parse(r) if parse else True)
        except Exception:
            return False, None
    prom_ok, _ = ok("http://prometheus:9090/-/ready")
    graf_ok, gdet = ok("http://grafana:3000/api/health", lambda r: r.json())
    am_ok, _ = ok("http://alertmanager:9093/api/v2/status")
    loki_ok, _ = ok("http://loki:3100/ready")
    # latest sample
    if points:
        ts, p95_s, jitter_ms, loss_pct, mbps = points[-1]
    else:
        p95_s=jitter_ms=loss_pct=mbps=0.0
    # tickets
    from pathlib import Path
    tdir = Path(CFG["TICKETS_DIR"]) if CFG.get("TICKETS_DIR") else Path("tickets")
    files = sorted(tdir.glob("ticket-*.json"))
    last = files[-1].name if files else None
    return {
        "app": {"ok": True},
        "prometheus": {"ok": prom_ok},
        "grafana": {"ok": graf_ok, "info": gdet or {}},
        "alertmanager": {"ok": am_ok},
        "loki": {"ok": loki_ok},
        "sample": {
            "p95_s": float(p95_s),
            "jitter_ms": float(jitter_ms),
            "loss_pct": float(loss_pct),
            "throughput_mbps": float(mbps),
            "anomaly": float(last_score),
        },
        "tickets": {"count": len(files), "last": last},
    }
