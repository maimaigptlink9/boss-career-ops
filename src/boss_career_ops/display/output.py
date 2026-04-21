import json
import sys
from pathlib import Path
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


def _serialize(envelope: dict) -> str:
    return json.dumps(envelope, ensure_ascii=False, indent=2)


def output_json(
    command: str,
    data: Any = None,
    pagination: dict | None = None,
    hints: dict | None = None,
    output: str | Path | None = None,
):
    envelope = format_envelope(
        ok=True,
        command=command,
        data=data,
        pagination=pagination,
        hints=hints,
    )
    text = _serialize(envelope)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text)


def output_error(
    command: str,
    message: str,
    code: str,
    hints: dict | None = None,
    output: str | Path | None = None,
):
    envelope = format_envelope(
        ok=False,
        command=command,
        error={"message": message, "code": code},
        hints=hints,
    )
    text = _serialize(envelope)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text)
