"""Alert when high-severity anomalies are detected."""

from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage

from pulsegrid.config import DELTA
from pulsegrid.io.delta_writer import read_delta_table

HIGH_SEVERITIES = {"high", "critical", "severe"}


def _load_anomalies(city: str) -> list[dict]:
    path = DELTA / "gold" / "anomaly_signals"
    if not path.exists():
        return []
    df = read_delta_table(path)
    if df.empty:
        return []
    if "city" in df.columns:
        df = df[df["city"] == city]
    rows = df.to_dict(orient="records")
    return [r for r in rows if str(r.get("severity", "")).lower() in HIGH_SEVERITIES]


def _slack(webhook: str, text: str) -> None:
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def _email(to_addr: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to_addr
    msg["From"] = os.getenv("PULSEGRID_ALERT_EMAIL_FROM", to_addr)
    msg.set_content(body)
    with smtplib.SMTP(os.getenv("PULSEGRID_SMTP_HOST", "localhost"), 25) as smtp:
        smtp.send_message(msg)


def notify_high_severity(city: str) -> int:
    """Send alerts for high-severity anomalies. Returns count alerted."""
    hits = _load_anomalies(city)
    if not hits:
        return 0
    lines = [
        f"AQ PulseGrid — {len(hits)} high-severity anomaly signal(s) for {city}:",
        "",
    ]
    for h in hits[:10]:
        lines.append(
            f"• {h.get('signal_type')} | {h.get('metric')} | z={h.get('z_score')} | {h.get('message')}"
        )
    text = "\n".join(lines)
    webhook = os.getenv("PULSEGRID_SLACK_WEBHOOK_URL", "").strip()
    email_to = os.getenv("PULSEGRID_ALERT_EMAIL_TO", "").strip()
    if webhook:
        _slack(webhook, text)
    if email_to:
        _email(email_to, f"PulseGrid alert: {city}", text)
    if not webhook and not email_to:
        print(text)
    return len(hits)


def main() -> int:
    import sys

    from pulsegrid.config import load_dotenv

    load_dotenv()
    city = sys.argv[1] if len(sys.argv) > 1 else "chicago"
    n = notify_high_severity(city)
    print(f"Alerted on {n} high-severity signal(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
