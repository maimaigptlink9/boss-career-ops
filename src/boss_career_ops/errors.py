from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class BCOError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)


class ConfigError(BCOError):
    pass


class PlatformError(BCOError):
    pass


class PipelineError(BCOError):
    pass


class AuthError(BCOError):
    pass


class EvaluationError(BCOError):
    pass


@dataclass
class Result:
    ok: bool
    data: Any = None
    error: str | None = None
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.ok:
            return {"ok": True, "data": self.data}
        d: dict[str, Any] = {"ok": False, "error": self.error}
        if self.code:
            d["code"] = self.code
        return d

    @staticmethod
    def success(data: Any = None) -> Result:
        return Result(ok=True, data=data)

    @staticmethod
    def failure(error: str, code: str = "INTERNAL_ERROR") -> Result:
        return Result(ok=False, error=error, code=code)
