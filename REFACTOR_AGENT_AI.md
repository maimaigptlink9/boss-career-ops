# 重构：移除云端 LLM API，改用 Agent 直接编排 AI 任务

## 背景

项目运行在 AI Agent 环境中（Trae/Claude Code/OpenClaw 等），Agent 本身具备 LLM 能力。
当前架构通过 `ai/provider.py` 调用外部 OpenAI 兼容 API 来完成 AI 任务（评估/润色/摘要/面试准备），
这是多余的——Agent 可以直接完成这些任务，无需绕道外部 API。

## 核心思路

**控制权反转**：从"Python 驱动 → 构造 Prompt → 调 API → 解析 JSON"变为
"Agent 驱动 → 读数据 → 思考 → 调 Python 工具写入结果"。

不再让 Agent 假装自己是 JSON API，而是让 Python 暴露工具给 Agent 调用。

## 阶段一：删除 ai/ 包及相关配置

### 删除文件

| 文件 | 原因 |
|------|------|
| `src/boss_career_ops/ai/__init__.py` | 整个 ai 包删除 |
| `src/boss_career_ops/ai/config.py` | 不再需要 API Key/模型配置 |
| `src/boss_career_ops/ai/provider.py` | 不再需要 Provider 抽象 |

### 删除命令

| 文件 | 原因 |
|------|------|
| `src/boss_career_ops/commands/ai_config.py` | `bco ai-config` 命令不再需要 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `src/boss_career_ops/cli/main.py` | 删除 `ai-config` 命令注册，删除相关 import |
| `src/boss_career_ops/commands/doctor.py` | 移除对 `ai.yml` 的诊断检查，移除 `AIConfig` 相关逻辑 |

### 清理引用

搜索所有 `from boss_career_ops.ai` 和 `import ai` 的引用，逐一移除：
- `ai.provider.get_provider` → 删除调用，业务逻辑由 Agent 接管
- `ai.config.load_ai_config` / `save_ai_config` → 删除
- `ai.config.AIConfig` → 删除

## 阶段二：删除业务模块中的 AI 调用逻辑

### evaluator/ai_scorer.py — 删除整个文件

`AIEvaluator` 类的全部职责（构造 Prompt、调 API、解析 JSON、重试、回退）由 Agent 接管。
保留 `evaluator/engine.py`（规则引擎）作为 Agent 输出异常时的校验兜底。
保留 `evaluator/scorer.py`（`score_to_grade()` / `get_recommendation()`）作为统一评分转换。

### resume/generator.py — 删除 `_ai_polish()` 方法

AI 润色由 Agent 完成，`_ai_polish()` 方法及其依赖的 Prompt 构造、章节校验逻辑全部删除。
保留 `_customize_cv()`（规则回退）和 PDF 生成流程。

### commands/chatmsg.py — 删除 `_summarize_with_ai()` 函数

聊天摘要由 Agent 完成，`_summarize_with_ai()` 及其 Prompt 构造、JSON 解析逻辑全部删除。
保留规则回退逻辑（简单统计）。

### commands/interview.py — 删除 `_ai_interview_prep()` 函数

面试准备由 Agent 完成，`_ai_interview_prep()` 及其 Prompt 构造、JSON 解析逻辑全部删除。
此模块无规则回退，Agent 不可用时仍报错。

### commands/ai_evaluate.py — 删除整个文件

`bco ai-evaluate` 命令由 Agent 直接调 `bco evaluate` + Agent 思考替代。

### commands/ai_evaluate_batch.py — 删除整个文件

批量 AI 评估由 Agent 循环调用 `bco evaluate` + Agent 思考替代。

## 阶段三：新增 Agent 工具暴露层

### 新增文件：`src/boss_career_ops/agent/__init__.py`

空文件，包标识。

### 新增文件：`src/boss_career_ops/agent/tools.py`

暴露 Agent 可调用的数据读取和结果写入函数。这些函数是对 PipelineManager + CacheStore 的薄封装，
Agent 通过 `bco` CLI 或直接 import 使用。

```python
# Agent 可读的数据
def get_job_detail(job_id: str) -> dict | None:
    """读取职位详情，含 Pipeline data 中的所有评估结果"""

def get_chat_messages(security_id: str) -> list[dict]:
    """读取与某联系人的聊天记录"""

def get_profile() -> dict:
    """读取个人档案（profile.yml）"""

def get_cv() -> str:
    """读取简历内容（cv.md）"""

def list_pipeline_jobs(stage: str | None = None) -> list[dict]:
    """列出 Pipeline 中的职位，可按阶段筛选"""

def get_job_with_ai_result(job_id: str) -> dict | None:
    """读取职位详情 + 关联的 AI 结果"""

# Agent 可写的操作
def write_evaluation(job_id: str, score: float, grade: str, analysis: str, scores_detail: dict | None = None) -> None:
    """写入评估结果到 Pipeline + ai_results 表"""

def write_resume(job_id: str, markdown_content: str) -> None:
    """写入润色后的简历 Markdown"""

def write_chat_summary(security_id: str, summary_data: dict) -> None:
    """写入聊天摘要"""

def write_interview_prep(job_id: str, prep_data: dict) -> None:
    """写入面试准备方案"""
```

### 新增 CLI 命令：`bco agent-evaluate`

作为 Agent 评估职位的入口。Agent 执行此命令时：
1. 从 Pipeline/Cache 读取职位数据
2. 输出结构化的职位信息供 Agent 分析
3. Agent 思考后，调用 `write_evaluation()` 写入结果

命令参数：
- `bco agent-evaluate <job_id>` — 输出单个职位供 Agent 评估
- `bco agent-evaluate --stage 发现 --limit 10` — 输出待评估职位列表

### 新增 CLI 命令：`bco agent-save`

Agent 统一的结果写入入口：
- `bco agent-save evaluate --job-id <id> --score 4.2 --grade B --analysis "..."` — 保存评估
- `bco agent-save chat-summary --security-id <id> --summary "..."` — 保存聊天摘要
- `bco agent-save interview-prep --job-id <id> --data '{"tech_questions": [...]}'` — 保存面试准备
- `bco agent-save resume --job-id <id> --content "..."` — 保存简历润色

## 阶段四：新增 ai_results 持久化表

### 在 pipeline/manager.py 中新增表

```sql
CREATE TABLE IF NOT EXISTS ai_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     TEXT NOT NULL,
    task_type  TEXT NOT NULL,
    result     TEXT NOT NULL,
    source     TEXT DEFAULT 'agent',
    created_at REAL NOT NULL,
    UNIQUE(job_id, task_type)
);
```

### task_type 枚举

| 值 | 说明 |
|---|---|
| `evaluate` | AI 评估结果（含推理过程） |
| `resume` | 简历润色结果（Markdown） |
| `chat_summary` | 聊天摘要 |
| `interview_prep` | 面试准备方案 |
| `company_research` | 公司研究 |

### 新增 PipelineManager 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `save_ai_result` | `(job_id, task_type, result, source='agent')` | 保存 AI 结果（UNIQUE 冲突时覆盖） |
| `get_ai_result` | `(job_id, task_type) -> dict \| None` | 获取指定类型 AI 结果 |
| `get_ai_results` | `(job_id) -> list[dict]` | 获取职位所有 AI 结果 |

## 阶段五：修改现有命令

### commands/evaluate.py

当前已有规则引擎评估。修改为：
- 评估完成后，检查是否有 Agent 写入的 `ai_results` 评估数据
- 如果有，用 Agent 评估的 score/grade 覆盖规则引擎的结果
- 保留规则引擎评估作为基线和校验

### commands/resume.py

修改为：
- 生成简历时，检查 `ai_results` 中是否有 Agent 润色后的 Markdown
- 如果有，直接使用润色后的内容生成 PDF
- 如果没有，使用规则逻辑 `_customize_cv()` 生成

### commands/chatmsg.py

修改 `bco chat-summary` 命令：
- 先检查 `ai_results` 中是否有 Agent 生成的摘要
- 如果有，直接输出
- 如果没有，使用规则回退

### commands/interview.py

修改为：
- 先检查 `ai_results` 中是否有 Agent 生成的面试准备
- 如果有，直接输出
- 如果没有，返回错误（interview 无规则回退）

### cli/main.py

- 删除 `ai-config` 命令注册
- 删除 `ai-evaluate` 命令注册
- 删除 `ai-evaluate-batch` 命令注册
- 新增 `agent-evaluate` 命令注册
- 新增 `agent-save` 命令注册

## 阶段六：更新测试

### 删除测试

| 文件 | 原因 |
|------|------|
| `tests/test_ai_scorer.py` | `AIEvaluator` 类已删除 |
| `tests/test_ai_evaluate.py` | `ai-evaluate` 命令已删除 |

### 新增测试

| 文件 | 测试内容 |
|------|----------|
| `tests/test_ai_results.py` | `ai_results` 表 CRUD、UNIQUE 约束、JSON 序列化 |
| `tests/test_agent_tools.py` | Agent 工具函数的输入输出验证 |

### 修改测试

| 文件 | 改动 |
|------|------|
| `tests/test_commands.py` | 移除 `ai-config`/`ai-evaluate`/`ai-evaluate-batch` 相关测试 |
| `tests/test_cli.py` | 移除已删除命令的 CLI 注册测试 |
| `tests/test_pipeline_manager.py` | 新增 `save_ai_result`/`get_ai_result` 测试 |

## 阶段七：更新项目文档

| 文件 | 改动 |
|------|------|
| `CLAUDE.md` | 移除"AI 优先回退"决策描述，新增"Agent 编排"决策描述 |
| `skills/boss-career-ops/skill.md` | 移除 `ai-config` 相关内容，新增 Agent 驱动 AI 的工作流 |
| `README.md` | 移除 AI 配置章节，更新架构描述 |

## 文件变更总览

### 删除（8 个文件）

```
src/boss_career_ops/ai/__init__.py
src/boss_career_ops/ai/config.py
src/boss_career_ops/ai/provider.py
src/boss_career_ops/evaluator/ai_scorer.py
src/boss_career_ops/commands/ai_config.py
src/boss_career_ops/commands/ai_evaluate.py
src/boss_career_ops/commands/ai_evaluate_batch.py
tests/test_ai_scorer.py
tests/test_ai_evaluate.py
```

### 新增（4 个文件）

```
src/boss_career_ops/agent/__init__.py
src/boss_career_ops/agent/tools.py
src/boss_career_ops/commands/agent_evaluate.py
src/boss_career_ops/commands/agent_save.py
tests/test_ai_results.py
tests/test_agent_tools.py
```

### 修改（10+ 个文件）

```
src/boss_career_ops/cli/main.py              — 命令注册调整
src/boss_career_ops/commands/doctor.py        — 移除 AI 诊断
src/boss_career_ops/commands/evaluate.py      — 读取 Agent 评估结果
src/boss_career_ops/commands/resume.py        — 读取 Agent 润色结果
src/boss_career_ops/commands/chatmsg.py       — 删除 _summarize_with_ai，读取 Agent 摘要
src/boss_career_ops/commands/interview.py     — 删除 _ai_interview_prep，读取 Agent 结果
src/boss_career_ops/resume/generator.py       — 删除 _ai_polish
src/boss_career_ops/pipeline/manager.py       — 新增 ai_results 表和方法
src/boss_career_ops/evaluator/__init__.py     — 移除 AIEvaluator 导出
CLAUDE.md                                     — 架构决策更新
skills/boss-career-ops/skill.md               — 工作流更新
README.md                                     — 文档更新
tests/test_commands.py                        — 测试调整
tests/test_cli.py                             — 测试调整
tests/test_pipeline_manager.py                — 新增 ai_results 测试
```

## 实施顺序

1. **阶段一** → 先删除 `ai/` 包，确保所有 import 清理干净，`uv run pytest` 通过
2. **阶段四** → 新增 `ai_results` 表，确保 PipelineManager 测试通过
3. **阶段二** → 删除业务模块中的 AI 调用逻辑，每删一个模块跑一次测试
4. **阶段三** → 新增 Agent 工具层和 CLI 命令，编写测试
5. **阶段五** → 修改现有命令读取 Agent 结果
6. **阶段六** → 更新测试
7. **阶段七** → 更新文档

每个阶段完成后 `uv run pytest` 必须通过。

## Agent 工作流（重构后）

### 评估流程

```
用户: "帮我评估这个职位"
Agent:
  1. bco agent-evaluate <job_id>          # 读取职位数据
  2. [Agent 思考：分析 JD、匹配技能、评估薪资、考虑地点...]
  3. bco agent-save evaluate --job-id <id> --score 4.2 --grade B --analysis "..."
  4. bco evaluate <security_id>           # 可选：规则引擎交叉验证
```

### 简历润色流程

```
用户: "帮我针对这个职位定制简历"
Agent:
  1. 读取 ~/.bco/cv.md                    # 原始简历
  2. bco agent-evaluate <job_id>          # 读取 JD
  3. [Agent 思考：提取 JD 关键词、优化经历描述、注入 ATS 关键词...]
  4. bco agent-save resume --job-id <id> --content "# 简历\n..."
  5. bco resume <job_id> --format pdf     # 使用 Agent 润色内容生成 PDF
```

### 聊天摘要流程

```
用户: "总结一下和这个 HR 的对话"
Agent:
  1. bco chatmsg <security_id>            # 读取聊天记录
  2. [Agent 思考：总结要点、判断语气、建议下一步...]
  3. bco agent-save chat-summary --security-id <id> --data '{"summary":"...","sentiment":"positive"}'
```

### 面试准备流程

```
用户: "帮我准备这个职位的面试"
Agent:
  1. bco agent-evaluate <job_id>          # 读取职位+公司信息
  2. [Agent 思考：技术问题、STAR 故事、反问、简历可能被问到的问题...]
  3. bco agent-save interview-prep --job-id <id> --data '{"tech_questions":[...],"star_stories":[...]}'
```
