"""BOSS直聘 AI 求职全流程系统"""
try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("boss-career-ops")
except Exception:
    __version__ = "0.0.0"
