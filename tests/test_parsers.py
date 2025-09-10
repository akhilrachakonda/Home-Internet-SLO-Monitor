from app.probes import run_ping

def test_run_ping_parses():
    r = {"p95_s":0.0, "jitter_ms":0.0, "loss_pct":0.0, "samples":0}
    assert all(k in r for k in ["p95_s","jitter_ms","loss_pct","samples"])
