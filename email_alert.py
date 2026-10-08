"""SMTP email alert module."""

import smtplib
from email.message import EmailMessage


def send_alert(config: dict, subject: str, body: str) -> None:
    email = config["email"]

    if not email.get("enabled", True):
        return

    host = email.get("smtp_host", "localhost")
    port = int(email.get("smtp_port", 25))
    sender = email["from"]
    recipients = email.get("to", [])

    if isinstance(recipients, str):
        recipients = [recipients]

    if not recipients:
        raise ValueError("At least one email recipient must be configured")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    username = email.get("username", "")
    password = email.get("password", "")
    use_tls = bool(email.get("use_tls", False))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()

        if username:
            smtp.login(username, password)

        smtp.send_message(message)
