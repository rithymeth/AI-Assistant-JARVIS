import smtplib
from email.mime.text import MIMEText

from config.settings import ACCESS_CODE, NOTIFY_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and NOTIFY_EMAIL)


def send_access_code_email(lan_url: str) -> tuple[bool, str]:
    """Best-effort, never raises — startup shouldn't fail because email did.
    Returns (sent, message) so the caller can print a clear status either way."""
    if not is_configured():
        return False, "not configured (set SMTP_HOST/SMTP_USER/SMTP_PASSWORD/NOTIFY_EMAIL in .env)"

    msg = MIMEText(f"Javi is running.\n\nOpen from your phone: {lan_url}\nAccess code: {ACCESS_CODE}\n")
    msg["Subject"] = "Javi is online"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True, f"sent to {NOTIFY_EMAIL}"
    except Exception as e:
        return False, f"failed: {e}"
