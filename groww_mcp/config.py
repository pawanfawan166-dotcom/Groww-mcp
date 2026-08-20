from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    access_token: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    totp_secret: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        access_token = os.getenv("GROWW_ACCESS_TOKEN")
        api_key = os.getenv("GROWW_API_KEY")
        api_secret = os.getenv("GROWW_API_SECRET") or os.getenv("GROWW_SECRET")
        totp_secret = os.getenv("GROWW_TOTP_SECRET") or os.getenv("TOTP_SECRET")

        credentials = os.getenv("GROWW_CREDENTIALS")
        if credentials:
            parsed = _parse_credentials(credentials)
            access_token = access_token or parsed.get("access_token")
            api_key = api_key or parsed.get("api_key")
            api_secret = api_secret or parsed.get("api_secret") or parsed.get("secret")
            totp_secret = totp_secret or parsed.get("totp_secret") or parsed.get("totp")

        return cls(
            access_token=access_token,
            api_key=api_key,
            api_secret=api_secret,
            totp_secret=totp_secret,
        )

    def has_credentials(self) -> bool:
        if self.access_token:
            return True
        if self.api_key and (self.totp_secret or self.api_secret):
            return True
        return False


def _parse_credentials(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("GROWW_CREDENTIALS must be valid JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("GROWW_CREDENTIALS must be a JSON object.")
    return data
