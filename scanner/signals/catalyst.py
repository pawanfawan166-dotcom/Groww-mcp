"""Catalyst detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CatalystSignals:
    score: float
    details: list[str]
    primary_catalyst: str | None


KEYWORDS = (
    "result",
    "earnings",
    "order",
    "contract",
    "dividend",
    "upgrade",
    "downgrade",
    "deal",
    "block",
    "bulk",
    "approval",
    "regulatory",
    "government",
    "guidance",
    "acquisition",
    "merger",
    "split",
    "bonus",
)


def analyze_catalysts(catalysts: list[str]) -> CatalystSignals:
    if not catalysts:
        return CatalystSignals(score=0.0, details=["No material catalyst detected"], primary_catalyst=None)

    score = 4.0
    details = []
    primary = catalysts[0]

    text = " ".join(catalysts).lower()
    hits = [kw for kw in KEYWORDS if kw in text]
    if hits:
        score += min(4.0, len(hits) * 1.5)
        details.append(f"Catalyst keywords: {', '.join(hits[:4])}")

    if len(catalysts) >= 2:
        score += 2.0
        details.append("Multiple recent news items")

    score = min(score, 10.0)
    details.append(primary[:120])
    return CatalystSignals(score=score, details=details, primary_catalyst=primary)
