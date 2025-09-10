from pathlib import Path
from datetime import datetime
import json

class TicketSink:
    def __init__(self, dirpath="tickets"):
        self.base = Path(dirpath)
        self.base.mkdir(parents=True, exist_ok=True)
        self.count = 0
    def create(self, title, window, summary, plots):
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        f = self.base / f"ticket-{ts}.json"
        payload = {"title": title, "window": window, "summary": summary, "plots": plots}
        f.write_text(json.dumps(payload, indent=2))
        self.count += 1
        return str(f)
