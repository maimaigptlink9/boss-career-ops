import json
import os
import base64
import hashlib
import portalocker
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

TOKEN_DIR = BCO_HOME
TOKEN_FILE = TOKEN_DIR / "tokens.enc"
LOCK_FILE = TOKEN_DIR / "tokens.lock"


def _get_machine_key() -> bytes:
    home_str = str(Path.home())
    home_hash = hashlib.sha256(home_str.encode()).hexdigest()
    try:
        username = os.getlogin()
    except OSError:
        username = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
    machine_id = f"{os.name}-{username}-{home_hash}"
    salt = b"boss-career-ops-salt-v3"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))


# 兼容旧版本 salt 的解密尝试
def _get_machine_key_legacy_v2() -> bytes:
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


class TokenStore(metaclass=SingletonMeta):

    def __init__(self):
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        self._fernet: Fernet | None = None

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            self._fernet = Fernet(_get_machine_key())
        return self._fernet

    def save(self, tokens: dict[str, Any]):
        data = json.dumps(tokens, ensure_ascii=False).encode("utf-8")
        encrypted = self.fernet.encrypt(data)
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
        try:
            with open(str(TOKEN_FILE), "rb") as f:
                encrypted = f.read()
        except Exception as e:
            logger.error("Token 读取失败: %s", e)
            return None
        try:
            data = self.fernet.decrypt(encrypted)
            return json.loads(data.decode("utf-8"))
        except Exception:
            pass
        # 尝试用旧版本 salt 解密（兼容 v2）
        try:
            legacy_fernet = Fernet(_get_machine_key_legacy_v2())
            data = legacy_fernet.decrypt(encrypted)
            logger.info("Token 使用旧版本密钥解密成功，建议重新登录以升级")
            return json.loads(data.decode("utf-8"))
        except Exception:
            pass
        logger.error("Token 解密失败")
        return None

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
