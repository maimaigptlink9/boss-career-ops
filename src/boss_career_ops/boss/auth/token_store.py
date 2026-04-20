import json
import os
import shutil
import base64
import hashlib
import portalocker
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.config.settings import BCO_HOME, LEGACY_HOME
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

_LEGACY_TOKEN_DIR = LEGACY_HOME
TOKEN_DIR = BCO_HOME
TOKEN_FILE = TOKEN_DIR / "tokens.enc"
LOCK_FILE = TOKEN_DIR / "tokens.lock"


def _migrate_legacy_tokens():
    if _LEGACY_TOKEN_DIR.exists() and not TOKEN_DIR.exists():
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        legacy_tokens = _LEGACY_TOKEN_DIR / "tokens.enc"
        if legacy_tokens.exists():
            shutil.copy2(str(legacy_tokens), str(TOKEN_FILE))
            logger.info("已从 %s 迁移 Token 到 %s", _LEGACY_TOKEN_DIR, TOKEN_DIR)


def _get_machine_key() -> bytes:
    home_str = str(Path.home())
    home_hash = hashlib.sha256(home_str.encode()).hexdigest()
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    machine_id = f"{os.name}-{username}-{home_hash}"
    salt = b"boss-career-ops-salt-v2"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))


def _get_legacy_machine_key() -> bytes:
    home_str = str(Path.home())
    home_hash = hashlib.sha256(home_str.encode()).hexdigest()
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    machine_id = f"{os.name}-{username}-{home_hash}"
    salt = b"boss-career-ops-salt-v1"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))


class TokenStore(metaclass=SingletonMeta):

    def __init__(self):
        _migrate_legacy_tokens()
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(_get_machine_key())

    def save(self, tokens: dict[str, Any]):
        data = json.dumps(tokens, ensure_ascii=False).encode("utf-8")
        encrypted = self._fernet.encrypt(data)
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        lock_fd = None
        try:
            lock_fd = open(str(LOCK_FILE), "w")
            portalocker.lock(lock_fd, portalocker.LOCK_EX)
            with open(str(TOKEN_FILE), "wb") as f:
                f.write(encrypted)
            logger.info("Token 已保存")
        finally:
            if lock_fd:
                try:
                    portalocker.unlock(lock_fd)
                except Exception:
                    pass
                lock_fd.close()

    def load(self) -> dict[str, Any] | None:
        if not TOKEN_FILE.exists():
            return None
        encrypted = None
        try:
            with open(str(TOKEN_FILE), "rb") as f:
                encrypted = f.read()
        except Exception as e:
            logger.error("Token 读取失败: %s", e)
            return None
        for key_func in [_get_machine_key, _get_legacy_machine_key]:
            try:
                fernet = Fernet(key_func())
                data = fernet.decrypt(encrypted)
                result = json.loads(data.decode("utf-8"))
                if key_func is _get_legacy_machine_key:
                    self.save(result)
                    logger.info("已用新密钥重新加密 Token")
                return result
            except Exception:
                continue
        logger.error("Token 解密失败（新旧密钥均无法解密）")
        return None

    def clear(self):
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        logger.info("Token 已清除")

    def check_quality(self) -> dict:
        tokens = self.load()
        if not tokens:
            return {"ok": False, "missing": ["all"], "message": "无 Token，请运行 bco login"}
        missing = []
        if "wt2" not in tokens or not tokens["wt2"]:
            missing.append("wt2")
        has_stoken = any(tokens.get(a) for a in ["stoken", "__zp_stoken__"])
        if not has_stoken:
            missing.append("stoken")
        if missing:
            return {"ok": False, "missing": missing, "message": f"Token 不完整，缺少: {', '.join(missing)}"}
        return {"ok": True, "missing": [], "message": "Token 有效"}
