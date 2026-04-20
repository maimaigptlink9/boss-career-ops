from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CommandType(str, Enum):
    PING = "ping"
    GET_COOKIES = "get_cookies"
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    SCREENSHOT = "screenshot"
    EXECUTE_JS = "execute_js"


@dataclass
class BridgeCommand:
    type: CommandType
    params: dict[str, Any] = field(default_factory=dict)
    id: str = ""


@dataclass
class BridgeResult:
    ok: bool = True
    data: Any = None
    error: str = ""
    id: str = ""
