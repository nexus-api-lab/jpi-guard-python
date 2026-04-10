from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ScanResponse


class JpiGuardError(Exception):
    """Raised when the jpi-guard API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class InjectionDetectedError(Exception):
    """Raised by guard_or_raise() when prompt injection is detected."""

    def __init__(self, result: "ScanResponse") -> None:
        types = [d["type"] for d in result.get("detections", [])]
        score = result.get("risk_score", 0.0)
        super().__init__(
            f"Prompt injection detected [{', '.join(types)}] — risk: {score:.2f}"
        )
        self.result = result
