"""One-shot Resend delivery check. Does not print secrets."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import resend


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_env(root / ".env")
    api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    from_email = (os.environ.get("RESEND_FROM_EMAIL") or "").strip()
    frontend = (os.environ.get("FRONTEND_PUBLIC_URL") or "").strip()
    to_email = "office.pramanik@gmail.com"

    print(f"key_present={bool(api_key)} key_prefix={api_key[:3] if api_key else ''}")
    print(f"from={from_email!r}")
    print(f"frontend={frontend!r}")
    print(f"to={to_email}")

    if not api_key or not from_email:
        print("SKIP: RESEND_API_KEY or RESEND_FROM_EMAIL missing")
        return 2

    resend.api_key = api_key
    try:
        result = resend.Emails.send(
            {
                "from": from_email,
                "to": [to_email],
                "subject": "DashNotes Resend check",
                "html": (
                    "<p>This is a delivery check from DashNotes.</p>"
                    "<p>If you received this, Resend is working.</p>"
                ),
                "text": "This is a delivery check from DashNotes.",
            }
        )
    except Exception as exc:
        print(f"send_fail={type(exc).__name__}: {exc}")
        return 1

    email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
    print(f"send_ok id={email_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
