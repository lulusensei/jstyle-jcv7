"""Send the daily report by email (Gmail SMTP with app password).

Configuration via environment variables or ~/.jcv7-mail:
    JCV7_MAIL_TO      destination address
    JCV7_GMAIL_USER   gmail account (e.g. lkstnkv@gmail.com)
    JCV7_GMAIL_APP    gmail app password (NOT the account password)

The app password is created at https://myaccount.google.com/apppasswords
(2-step verification required). Never commit it to the repository.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def load_config() -> dict:
    cfg = {
        "to": os.environ.get("JCV7_MAIL_TO"),
        "user": os.environ.get("JCV7_GMAIL_USER"),
        "app": os.environ.get("JCV7_GMAIL_APP"),
    }
    path = os.path.expanduser("~/.jcv7-mail")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            key = {"to": "to", "user": "user", "app": "app"}.get(k.lower())
            if key and not cfg[key]:
                cfg[key] = v
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise SystemExit(
            f"missing mail config: {', '.join(missing)}\n"
            "set JCV7_MAIL_TO / JCV7_GMAIL_USER / JCV7_GMAIL_APP "
            "or create ~/.jcv7-mail with to=, user=, app= lines"
        )
    return cfg


def send_report(subject: str, body: str) -> None:
    cfg = load_config()
    msg = EmailMessage()
    msg["From"] = cfg["user"]
    msg["To"] = cfg["to"]
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(cfg["user"], cfg["app"])
        s.send_message(msg)
