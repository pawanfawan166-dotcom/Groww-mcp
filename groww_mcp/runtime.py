from __future__ import annotations

import os

from groww_mcp.config import Settings
from groww_mcp.groww_client import GrowwClient


def is_mock() -> bool:
    return os.getenv("GROWW_MOCK_MODE", "1").lower() in {"1", "true", "yes"} or not (
        os.getenv("GROWW_ACCESS_TOKEN")
        or os.getenv("GROWW_CREDENTIALS")
        or (
            os.getenv("GROWW_API_KEY")
            and (
                os.getenv("TOTP_SECRET")
                or os.getenv("GROWW_TOTP_SECRET")
                or os.getenv("GROWW_API_SECRET")
                or os.getenv("GROWW_SECRET")
            )
        )
    )


def client() -> GrowwClient:
    return GrowwClient(Settings.from_env())
