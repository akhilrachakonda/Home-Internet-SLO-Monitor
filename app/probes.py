import subprocess, statistics, re, json
from datetime import datetime

def run_ping(host: str, count: int = 10, degrade_flag: bool = False):
    out = subprocess.run(["ping", "-c", str(count), host], capture_output=True, text=True)
    text = out.stdout
    rtts = [float(m.group(1)) for m in re.finditer(r"time=(\d+\.\d+)", text)]
    loss_m = re.search(r"(\d+\.\d+|\d+)% packet loss", text)
    loss = float(loss_m.group(1)) if loss_m else 0.0
    p95 = sorted(rtts)[int(0.95*len(rtts))-1] / 1000 if rtts else 0.0  # seconds
    jitter = statistics.pstdev(rtts) if rtts else 0.0
    if degrade_flag:
        p95 += 0.05  # +50ms artificial
        jitter += 5
        loss = min(loss + 2.0, 100.0)
    return {
        "ts": datetime.utcnow().isoformat(),
        "p95_s": p95,
        "jitter_ms": jitter,
        "loss_pct": loss,
        "samples": len(rtts)
    }

def run_iperf(host: str, seconds: int = 5):
    out = subprocess.run(["iperf3", "-c", host, "-J", "-t", str(seconds)], capture_output=True, text=True)
    try:
        import json
        j = json.loads(out.stdout)
        mbps = j["end"]["sum_received"]["bits_per_second"]/1e6
    except Exception:
        mbps = 0.0
    return {"throughput_mbps": mbps}
