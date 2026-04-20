import logging
import re
from typing import Any


SENSITIVE_KEYS = {"password", "secret", "authorization", "wt2", "zp_token", "__zp_stoken__", "stoken", "token", "cookie", "session"}


def _mask_value(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return "***"
    return value[:visible] + "***"


def _mask_string_values(s: str) -> str:
    for key in SENSITIVE_KEYS:
        pattern = rf'({key}\s*[=:]\s*)(\S+)'
        s = re.sub(pattern, rf'\1***', s, flags=re.IGNORECASE)
    return s


def mask_sensitive(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: mask_sensitive(v) if not _is_sensitive_key(k) else _mask_value(str(v)) if isinstance(v, str) else "***"
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive(item) for item in data]
    elif isinstance(data, str):
        return _mask_string_values(data)
    return data


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    return any(s in key_lower for s in SENSITIVE_KEYS)


class SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = self._mask_string(record.msg)
            if isinstance(record.args, dict):
                record.args = mask_sensitive(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive(arg) if isinstance(arg, (dict, str)) else arg
                    for arg in record.args
                )
        except Exception:
            pass
        return True

    def _mask_string(self, s: str) -> str:
        for key in SENSITIVE_KEYS:
            pattern = rf'({key}\s*[=:]\s*)(\S+)'
            s = re.sub(pattern, rf'\1***', s, flags=re.IGNORECASE)
        return s


def get_logger(name: str = "boss_career_ops") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(SensitiveFilter())
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
