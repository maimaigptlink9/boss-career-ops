---
alwaysApply: true
---

#  Project Rules

## Python Environment

- **包管理器**: uv
- **Python Version**: 3.12
- **项目配置**: pyproject.toml

### Usage Rules
- 使用 `uv sync` 安装/同步项目依赖
- 使用 `uv run` 在项目虚拟环境中执行命令（如 `uv run bco doctor`）
- 使用 `uv add <package>` 添加新依赖（自动更新 pyproject.toml 和 uv.lock）
- 使用 `uv run python <script.py>` 运行 Python 脚本
- 不要使用 conda、pip 直接安装，所有依赖管理统一走 uv
