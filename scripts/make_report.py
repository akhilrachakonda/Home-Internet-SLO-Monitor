import os, json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
reports = BASE/"reports"; tickets = BASE/"tickets"
reports.mkdir(exist_ok=True)

week = os.environ.get("WEEK") or datetime.utcnow().strftime("%G-W%V")
html = [f"<h1>Internet SLO Weekly Report {week}</h1>"]
for t in sorted(tickets.glob("ticket-*.json")):
    data = json.loads(t.read_text())
    html.append(f"<h2>{data['title']}</h2>")
    html.append(f"<pre>{json.dumps(data['summary'], indent=2)}</pre>")
    for p in data.get("plots", []):
        rel = os.path.relpath(p, reports)
        html.append(f"<img src='{rel}' width='600'/>")

out = reports/f"week-{week}.html"
out.write_text("\n".join(html))

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    pdf = reports/f"week-{week}.pdf"
    c = canvas.Canvas(str(pdf), pagesize=A4)
    c.drawString(72, 800, f"Internet SLO Weekly Report {week}")
    c.drawString(72, 780, f"Tickets: {len(list(tickets.glob('ticket-*.json')))}")
    c.showPage(); c.save()
except Exception:
    pass
print(f"Report written to {out}")
