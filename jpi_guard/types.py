from __future__ import annotations

from typing import Literal, TypedDict


# ─── Request ─────────────────────────────────────────────────────────────────

Strictness = Literal["low", "medium", "high"]
ContentType = Literal["plaintext", "html", "markdown", "json"]
Language = Literal["auto", "ja", "en"]
OnTimeout = Literal["fail_open", "fail_close"]


# ─── Response ─────────────────────────────────────────────────────────────────

class Detection(TypedDict):
    type: str
    position: int
    original: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float


class ScanResponse(TypedDict):
    injection_detected: bool
    risk_score: float
    cleaned_content: str
    detections: list[Detection]
    removed_segments_count: int
    content_integrity_ratio: float
    safe_to_render: bool
    processing_time_ms: int
    request_id: str
