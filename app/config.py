import os, pathlib

CFG = {
    "TARGET_HOST": os.getenv("TARGET_HOST", "1.1.1.1"),
    "IPERF_HOST": os.getenv("IPERF_HOST", "iperf3"),
    "PING_COUNT": int(os.getenv("PING_COUNT", 10)),
    "PROBE_INTERVAL_SEC": int(os.getenv("PROBE_INTERVAL_SEC", 30)),
    "ANOMALY_WINDOW": int(os.getenv("ANOMALY_WINDOW", 120)),
    "ANOMALY_THRESHOLD": float(os.getenv("ANOMALY_THRESHOLD", 0.65)),
    "TICKETS_DIR": os.getenv("TICKETS_DIR", "tickets"),
    "REPORTS_DIR": os.getenv("REPORTS_DIR", "reports"),
}

pathlib.Path(CFG["TICKETS_DIR"]).mkdir(parents=True, exist_ok=True)
pathlib.Path(CFG["REPORTS_DIR"]).mkdir(parents=True, exist_ok=True)
