---
name: "boss-career-ops"
description: "BOSS直聘AI求职全流程CLI工具，覆盖搜索/评估/投递/沟通/面试/谈判闭环。Invoke when user asks about job search, BOSS直聘, 职位搜索, 投递, 打招呼, 面试, 薪资谈判, or any job-hunting operations."
---

# Boss-Career-Ops Skill

BOSS 直聘 AI 求职全流程系统。通过 `bco` CLI 命令完成从职位发现到拿到 offer 的完整闭环。

核心原则：**AI 评估推荐，人决定行动。系统自动执行高分职位，低分职位需人工确认。**

## 全局选项

| 选项 | 说明 |
|------|------|
| `bco --version` | 查看版本号 |
| `bco --help` | 查看帮助 |

## 会话启动流程

**每次用户提到求职/BOSS直聘相关话题时，必须按顺序执行以下检查：**

### 第 1 步：检查 bco 是否已安装

```bash
bco --version
```

- 若成功，说明已通过 `uv tool install` 或 `pip install` 全局安装，后续所有命令直接用 `bco <cmd>`
- 若命令不存在，检查是否为开发模式（当前目录存在 `pyproject.toml` 且包含 `boss-career-ops`）：
  - 开发模式：使用 `uv run bco <cmd>` 执行所有后续命令
  - 非开发模式，提示用户安装：
    - 推荐：`uv tool install boss-career-ops`
    - 备选：`pip install boss-career-ops`
    - 若上述安装失败，可从源码安装：`uv tool install git+https://github.com/maimaigptlink9/boss_career_ops.git`
    - 安装完成后重新执行本步骤确认

### 第 2 步：环境诊断

```bash
bco doctor
```

- 若输出 `ok: false` 且错误提示配置缺失，执行 `bco setup` 初始化，然后重新诊断
- 配置目录位于 `~/.bco/`（可通过 `BCO_HOME` 环境变量自定义根目录）

### 第 3 步：检查登录态

```bash
bco status
```

- 若未登录，执行 `bco login` 提示用户登录
- 登录方式 4 级降级：Cookie提取 → CDP → 二维码 → patchright，系统自动选择
- **登录需要用户交互**，Agent 必须等待用户完成操作：
  - Cookie 提取方式需要**管理员权限**运行终端
  - CDP 方式需要用户先启动 Chrome：`chrome.exe --remote-debugging-port=9222`
  - QR/patchright 方式会弹出浏览器窗口，需用户手动扫码或操作
  - Agent 不应跳过此步骤，必须确认登录成功后再继续

### 第 4 步：检查 AI 配置与个人档案

```bash
bco ai-config --show
```

- 若 `configured: false`，执行 `bco ai-config --api-key <key> --base-url <url> --model <model>` 配置 AI 服务
- AI 配置影响 `chat-summary`、`interview`、`negotiate` 命令，未配置时这些命令会返回 `AI_NOT_CONFIGURED` 错误

然后提醒用户编辑个人档案（评估和推荐的核心依赖）：

- `~/.bco/config/profile.yml` — 填写技能、期望薪资、偏好城市等结构化信息
- `~/.bco/cv.md` — 填写完整简历内容（Markdown 格式）

**未配置档案的后果**：
- `evaluate`：4/5 维度退化为固定中低分（2.5~3.0），评估结果无区分度
- `recommend`：不传城市和关键词参数，返回与用户意向无关的默认推荐
- `resume`：生成极简简历而非定制简历

## 输出协议

所有命令输出 JSON 到 stdout，统一信封格式：

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "<command_name>",
  "data": {},
  "pagination": {"page": 1, "has_more": true, "total": 15},
  "error": null,
  "hints": {"next_actions": ["..."]}
}
```

- `ok` 字段判断成败
- 错误信息在 `error.message`（中文）和 `error.code`（英文）
- `hints.next_actions` 建议下一步操作，应遵循执行

## 评估引擎：5 维评分体系

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 匹配度 | 30% | 技能、经验、学历与 JD 的匹配程度 |
| 薪资 | 25% | 薪资范围与预期的对比，行业竞争力 |
| 地点 | 15% | 通勤距离、城市偏好、远程可能性 |
| 发展 | 15% | 职业成长空间、技术栈前瞻性、团队规模 |
| 团队 | 15% | 公司阶段、团队文化、面试反馈信号 |

### 评分等级

| 等级 | 分数 | 含义 | 自动动作 |
|------|------|------|----------|
| A | 4.5-5.0 | 强烈推荐，立即行动 | 自动投递 |
| B | 3.5-4.4 | 值得投入，优先处理 | 自动打招呼 |
| C | 2.5-3.4 | 一般，需人工判断 | 需确认 |
| D | 1.5-2.4 | 不太匹配，谨慎考虑 | 需确认 |
| F | 0.0-1.4 | 不推荐 | 跳过 |

## 核心工作流

```
搜索职位 → 5维评估 → 自动/手动决策 → 简历定制 → 打招呼/投递 → 沟通跟进 → 面试准备 → 薪资谈判 → offer
```

## 命令完整参考

### 环境与认证

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco doctor` | 环境诊断 | `bco doctor` |
| `bco setup` | 初始化配置（首次使用） | `bco setup` |
| `bco login` | 登录（4级降级：Cookie→CDP→QR→patchright） | `bco login` |
| `bco status` | 检查登录态 | `bco status` |

### AI 配置

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco ai-config` | 配置 AI 服务 | `bco ai-config --api-key <key> --base-url <url> --model <model>` |
| | 配置 Provider 和参数 | `bco ai-config --provider openai_compat --max-tokens 4096 --temperature 0.7` |
| | 查看当前配置（API Key 脱敏） | `bco ai-config --show` |

支持的参数：`--api-key`、`--base-url`、`--model`、`--provider`、`--max-tokens`、`--temperature`、`--show`

### 职位搜索与评估

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco search` | 搜索职位 + 8维筛选 + 福利过滤 | `bco search <keyword> --city <city> --welfare <welfare> --page <n> --limit <n> --pages <n>` |
| `bco recommend` | 基于个人档案的个性化推荐 | `bco recommend` |
| `bco evaluate` | 5维评估（单个/批量） | `bco evaluate <security_id>` 或 `bco evaluate --from-search` |
| `bco auto-action` | 阈值驱动自动执行（无参数） | `bco auto-action` |
| `bco shortlist` | 精选列表（B级及以上，无参数） | `bco shortlist` |

### 投递与沟通

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco greet` | 打招呼 | `bco greet <security_id> <job_id>` |
| `bco batch-greet` | 批量打招呼（高斯延迟，最大10个） | `bco batch-greet <keyword> --city <city>` |
| `bco apply` | 投递简历 | `bco apply <security_id> <job_id>` |
| `bco resume` | 生成定制简历（MD/PDF） | `bco resume <job_id> --format <md\|pdf>` |

### 聊天管理

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco chat` | 聊天列表（不带 --export 时列出所有聊天） | `bco chat` |
| `bco chat` | 聊天导出 | `bco chat --export <csv\|json\|html\|md>` |
| `bco chatmsg` | 聊天消息历史 | `bco chatmsg <security_id>` |
| `bco chat-summary` | 聊天摘要（AI 增强，需 AI 配置） | `bco chat-summary <security_id>` |
| `bco mark` | 联系人标签 | `bco mark <security_id> --tag <tag>` |
| `bco exchange` | 交换联系方式 | `bco exchange <security_id> --type <phone\|wechat>` |

### 流水线与追踪

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco pipeline` | 求职流水线追踪（无参数） | `bco pipeline` |
| `bco follow-up` | 跟进提醒（无参数） | `bco follow-up` |
| `bco digest` | 每日摘要（无参数） | `bco digest` |

### 监控与导出

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco watch add` | 添加监控 | `bco watch add <name> <keyword> --city <city> --welfare <welfare>` |
| `bco watch list` | 列出监控 | `bco watch list` |
| `bco watch remove` | 移除监控 | `bco watch remove <name>` |
| `bco watch run` | 执行监控 | `bco watch run <name>` |
| `bco export` | 多格式导出 | `bco export <keyword> --city <city> -o <output> --format <csv\|json\|html\|md> --count <n>` |

### 面试与谈判

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco interview` | 面试准备（AI 增强，需 AI 配置） | `bco interview <job_id>` |
| `bco negotiate` | 薪资谈判辅助（AI 增强，需 AI 配置） | `bco negotiate <job_id>` |
| `bco dashboard` | 启动 TUI Dashboard（无参数） | `bco dashboard` |

## 错误码速查表

遇到 `ok: false` 时，根据 `error.code` 执行对应恢复动作：

| 错误码 | 含义 | 恢复动作 |
|--------|------|----------|
| `AUTH_REQUIRED` | 未登录 | `bco login` |
| `AUTH_EXPIRED` | 登录过期 | `bco login` |
| `TOKEN_REFRESH_FAILED` | Token 刷新失败 | `bco login` |
| `AI_NOT_CONFIGURED` | AI 未配置 | `bco ai-config --api-key <key>` |
| `RATE_LIMITED` | 频率过高 | 等待后重试 |
| `ACCOUNT_RISK` | 风控拦截 | 建议用 CDP Chrome 重试：`chrome.exe --remote-debugging-port=9222` |
| `GREET_LIMIT` | 今日打招呼次数用完 | 告知用户，次日再试 |
| `ALREADY_GREETED` | 已打过招呼 | 跳过此职位 |
| `NETWORK_ERROR` | 网络错误 | 重试 |
| `INVALID_PARAM` | 参数错误 | 修正参数后重试 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `BCO_HOME` | 配置根目录 | `~/.bco/` |

修改 `BCO_HOME` 后，所有配置文件（profile.yml、thresholds.yml、tokens.enc 等）均从新目录读取。

## 安全与合规规则

1. **严格遵守阈值配置**，不擅自降低自动执行标准
2. **所有写操作**（打招呼、投递）前确认用户意图
3. **速率限制**：系统内置高斯延迟，不要绕过
4. **敏感信息**（Token、Cookie）不输出到日志或对话
5. **批量操作上限**：batch-greet 最大 10 个，不要拆分绕过
6. 用户提到福利要求时使用 `--welfare` 参数
7. 评估后根据 `hints.next_actions` 建议下一步
8. 不要在未评估的情况下直接投递或打招呼
