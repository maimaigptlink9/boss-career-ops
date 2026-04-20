import json
import sys
from typing import Any


SCHEMA_VERSION = "1.0"


def format_envelope(
    ok: bool,
    command: str,
    data: Any = None,
    pagination: dict | None = None,
    error: dict | None = None,
    hints: dict | None = None,
) -> dict:
    result = {
        "ok": ok,
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "data": data,
        "pagination": pagination,
        "error": error,
        "hints": hints or {},
    }
    return result


def output_json(
    command: str,
    data: Any = None,
    pagination: dict | None = None,
    hints: dict | None = None,
):
    envelope = format_envelope(
        ok=True,
        command=command,
        data=data,
        pagination=pagination,
        hints=hints,
    )
    print(json.dumps(envelope, ensure_ascii=False, indent=2))


def output_error(
    command: str,
    message: str,
    code: str,
    hints: dict | None = None,
):
    envelope = format_envelope(
        ok=False,
        command=command,
        error={"message": message, "code": code},
        hints=hints,
    )
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
