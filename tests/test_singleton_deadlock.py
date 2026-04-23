"""
测试 SingletonMeta 嵌套单例创建时的死锁问题

根本原因：
SingletonMeta 使用 threading.Lock()（非可重入锁）。
当一个单例的 __init__ 内部创建另一个单例时，同一个线程
尝试二次获取同一把锁，导致永久阻塞（死锁）。

典型触发场景：
- AuthManager.__init__ 内创建 TokenStore() → 死锁
- BossClient.__init__ 内创建 TokenStore() + Thresholds() → 死锁

修复方案：
将 threading.Lock() 改为 threading.RLock()（可重入锁），
允许同一线程多次获取同一把锁。
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
from pathlib import Path

from boss_career_ops.config.singleton import SingletonMeta

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = [str(SRC_DIR)]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return env


def _run_snippet(snippet: str, timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    prelude = f"""
import os
import tempfile

os.environ["BCO_HOME"] = tempfile.mkdtemp(prefix="bco-test-")
"""
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(prelude + snippet)],
        cwd=REPO_ROOT,
        env=_subprocess_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_singleton_nested_creation_no_deadlock():
    """验证嵌套单例创建不会死锁（使用 RLock 修复后应通过）"""
    class Inner(metaclass=SingletonMeta):
        def __init__(self):
            self.value = "inner"

    class Outer(metaclass=SingletonMeta):
        def __init__(self):
            self.inner = Inner()

    SingletonMeta.reset(Inner)
    SingletonMeta.reset(Outer)

    result = []
    error = []

    def create_outer():
        try:
            obj = Outer()
            result.append(obj)
        except Exception as e:
            error.append(e)

    t = threading.Thread(target=create_outer)
    t.start()
    t.join(timeout=5)

    assert not error, f"嵌套创建单例时出错: {error}"
    assert len(result) == 1, "嵌套创建单例应在 5 秒内完成（不应死锁）"
    assert isinstance(result[0].inner, Inner)


def test_singleton_uses_rlock():
    """验证 SingletonMeta 使用 RLock 而非 Lock"""
    lock_type_name = type(SingletonMeta._lock).__name__
    assert lock_type_name == "RLock", (
        f"SingletonMeta._lock 应为 RLock（可重入锁），"
        f"当前为 {lock_type_name}，会导致嵌套单例创建死锁"
    )


def test_authmanager_creation_no_deadlock():
    """验证 AuthManager 创建不会死锁（其 __init__ 内创建 TokenStore）"""
    from boss_career_ops.boss.auth.manager import AuthManager
    from boss_career_ops.boss.auth.token_store import TokenStore

    SingletonMeta.reset(AuthManager)
    SingletonMeta.reset(TokenStore)

    result = []
    error = []

    def create_auth_manager():
        try:
            manager = AuthManager()
            result.append(manager)
        except Exception as e:
            error.append(e)

    t = threading.Thread(target=create_auth_manager)
    t.start()
    t.join(timeout=5)

    assert not error, f"AuthManager 创建时出错: {error}"
    assert len(result) == 1, "AuthManager 应在 5 秒内完成创建（不应死锁）"


def test_status_command_no_longer_deadlocks():
    result = _run_snippet(
        """
from click.testing import CliRunner
from boss_career_ops.cli.main import cli

CliRunner().invoke(cli, ["status"])
print("completed")
"""
    )
    assert result.returncode == 0, result.stderr
    assert "completed" in result.stdout


def test_auth_manager_init_no_longer_deadlocks():
    result = _run_snippet(
        """
from boss_career_ops.boss.auth.manager import AuthManager

AuthManager()
print("completed")
"""
    )
    assert result.returncode == 0, result.stderr
    assert "completed" in result.stdout


def test_singleton_meta_no_deadlock_when_nested():
    result = _run_snippet(
        """
from boss_career_ops.config.singleton import SingletonMeta


class Inner(metaclass=SingletonMeta):
    pass


class Outer(metaclass=SingletonMeta):
    def __init__(self):
        Inner()


Outer()
print("completed")
"""
    )
    assert result.returncode == 0, result.stderr
    assert "completed" in result.stdout


def test_token_store_init_returns_without_nested_singleton():
    result = _run_snippet(
        """
from boss_career_ops.boss.auth.token_store import TokenStore

TokenStore()
print("completed")
""",
        timeout=8.0,
    )
    assert result.returncode == 0, result.stderr
    assert "completed" in result.stdout
