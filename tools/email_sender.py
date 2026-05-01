import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MAX_RETRIES = 3
RETRY_DELAY = 5
SMTP_TIMEOUT = 10


def _load_config() -> dict:
    config = {
        "sender": os.getenv("EMAIL_SENDER"),
        "password": os.getenv("EMAIL_PASSWORD"),
        "recipient": os.getenv("EMAIL_RECIPIENT"),
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
    }
    missing = [k for k, v in config.items() if not v]
    if missing:
        raise EnvironmentError(f".env에 다음 항목이 없습니다: {', '.join(missing)}")
    return config


def send_email(subject: str, body: str, attachments: list = None) -> bool:
    if not subject or not isinstance(subject, str):
        raise ValueError("subject는 비어있지 않은 문자열이어야 합니다.")
    if not body or not isinstance(body, str):
        raise ValueError("body는 비어있지 않은 문자열이어야 합니다.")
    if attachments is None:
        attachments = []

    config = _load_config()

    msg = MIMEMultipart()
    msg["From"] = config["sender"]
    msg["To"] = config["recipient"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for filepath in attachments:
        path = Path(filepath)
        if not path.exists():
            print(f"[WARN] 첨부 파일 없음, 건너뜀: {path.name}")
            continue
        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={path.name}")
        msg.attach(part)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(config["host"], config["port"], timeout=SMTP_TIMEOUT) as server:
                server.starttls()
                server.login(config["sender"], config["password"])
                server.sendmail(config["sender"], config["recipient"], msg.as_string())
            print(f"[SUCCESS] 이메일 발송 완료 (시도 {attempt}/{MAX_RETRIES})")
            return True
        except Exception:
            print(f"[FAIL] 이메일 발송 실패 (시도 {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    print("[ERROR] 최대 재시도 초과, 발송 실패")
    return False


if __name__ == "__main__":
    send_email(
        subject="테스트 이메일",
        body="Contents Report 시스템 테스트입니다.",
    )
