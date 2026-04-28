# Boss-Career-Ops 优化方案

> 基于全量源码审查，覆盖 12 个核心模块、65 个测试文件、配置系统与依赖树。
> 生成日期：2026-04-26

---

## 一、P0 — 必须修复（逻辑 Bug / 架构违规）

### 1.1 评分引擎运算符优先级 Bug

**文件**: `src/boss_career_ops/evaluator/engine.py`

**问题**: `_score_salary()` 中条件判断运算符优先级错误：

```python
# 当前代码（错误）
if job_min is None or job_max is None and salary_desc:
    # 实际逻辑: (job_min is None) or (job_max is None and salary_desc)
    # 预期逻辑: (job_min is None or job_max is None) and salary_desc
```

**修改逻辑**:

1. 添加括号修正优先级：`if (job_min is None or job_max is None) and salary_desc:`
2. 编写测试覆盖此分支——构造 `job_min=None, salary_desc="10K-20K"` 的场景，验证走解析分支而非跳过
3. 全文搜索同类 `or ... and` 模式，排查其他潜在优先级问题

**验证**: `uv run pytest tests/test_evaluator_engine.py tests/test_evaluator_scorer.py -v`

---

### 1.2 Agent 图编排逻辑缺陷

**文件**: `src/boss_career_ops/agent/graph.py`, `src/boss_career_ops/agent/conditions.py`

**问题 A**: `"resume+apply"` 路由到 `"resume"` 节点，但 resume 节点执行后直接 END，apply 永远不会执行。

**问题 B**: 所有业务节点执行后直接到 END，无多步编排能力，无法实现"搜索→评估→打招呼→投递"链式流程。

**修改逻辑**:

1. **修复路由 bug**: 在 `conditions.py` 中将 `"resume+apply"` 路由到 `"resume"` 节点（保留），但在 `graph.py` 中为 resume 节点添加到 apply 节点的条件边：

   ```python
   # graph.py build_career_agent() 修改
   # 原来: graph.add_node("resume", resume_node) 后直接 add_edge("resume", END)
   # 改为: 根据状态中的 intent 决定下一步
   def route_after_resume(state):
       if "apply" in state.get("intent", ""):
           return "apply"
       return END

   graph.add_conditional_edges("resume", route_after_resume, {"apply": "apply", END: END})
   ```

2. **添加回环边**: 为所有业务节点添加回到 orchestrator 的条件边，实现多步编排：

   ```python
   def route_after_action(state):
       next_action = state.get("next_action")
       if next_action and next_action in NODE_NAMES:
           return next_action
       return END

   for node in [search_node, evaluate_node, resume_node, apply_node, gap_analysis_node]:
       graph.add_conditional_edges(node, route_after_action, {**{n: n for n in NODE_NAMES}, END: END})
   ```

3. **更新 AgentState**: 为 `errors` 字段添加 `Annotated[list[str], operator.add]` reducer，防止多节点追加错误时互相覆盖

4. **编写测试**:
   - 测试 `"resume+apply"` intent 完整执行两个节点
   - 测试 orchestrator 多步编排（搜索→评估→打招呼）
   - 测试 StateGraph 编译不报错

**验证**: `uv run pytest tests/test_agent_graph.py tests/test_agent_orchestrator.py -v`

---

### 1.3 MCP Tools 绕过持久化

**文件**: `src/boss_career_ops/mcp/tools.py`

**问题**: `evaluate_job` 工具直接调用 `EvaluationEngine`，评估结果不写入 `ai_results` 表，违反项目规则"MCP tool handler 必须调用 agent/tools.py"。

**修改逻辑**:

1. 将 `evaluate_job` 的 handler 从：

   ```python
   # 当前：直接调用 EvaluationEngine
   from boss_career_ops.evaluator.engine import EvaluationEngine
   engine = EvaluationEngine(...)
   result = engine.evaluate(job, profile)
   ```

   改为：

   ```python
   # 修改后：通过 agent/tools.py 调用，确保持久化
   from boss_career_ops.agent.tools import write_evaluation
   result = write_evaluation(job_id, evaluation_data)
   ```

2. 同理检查其余 8 个 MCP tool handler，确保全部通过 `agent/tools.py` 调用，不直接调用底层模块

3. 编写测试：调用 `evaluate_job` MCP tool 后，查询 `ai_results` 表验证数据已持久化

**验证**: `uv run pytest tests/test_mcp_tools.py -v`

---

### 1.4 Web Server 架构违规

**文件**: `src/boss_career_ops/web/server.py`

**问题 A**: 导入已删除的 `ai_config` 模块，违反 CLAUDE.md 规则。

**问题 B**: `api_update_profile()` 直接操作文件系统 + 手动 `SingletonMeta._instances.pop(Settings, None)` 强制重载单例。

**修改逻辑**:

1. **移除 ai_config 依赖**: 将 AI 配置相关端点改为通过 `agent/llm.py` 的 `get_llm()` 获取信息：

   ```python
   # 替换 from boss_career_ops.config import ai_config
   from boss_career_ops.agent.llm import get_llm, PROVIDER_DEFAULTS
   ```

2. **为 Settings 添加 reload() 方法**: 在 `config/singleton.py` 中：

   ```python
   class SingletonMeta(type):
       _instances = {}
       _lock = threading.Lock()

       def reload_instance(mcs, cls):
           """安全地重置并重新初始化单例"""
           with mcs._lock:
               mcs._instances.pop(cls, None)
           return cls()  # 下次访问会重新初始化
   ```

3. **api_update_profile() 改用 Settings.reload_instance()**:

   ```python
   # 替换 SingletonMeta._instances.pop(Settings, None)
   Settings.reload_instance()
   ```

4. 编写测试验证 reload 后配置确实更新

**验证**: `uv run pytest tests/test_web_server.py tests/test_config.py -v`

---

## 二、P1 — 应该修复（设计缺陷 / 安全 / 性能）

### 2.1 错误处理统一化

**文件**: 新建 `src/boss_career_ops/errors.py`，修改各模块

**修改逻辑**:

1. 定义统一异常层次：

   ```python
   class BCOError(Exception):
       """基础异常"""
       def __init__(self, message: str, code: str = "UNKNOWN"):
           self.message = message
           self.code = code
           super().__init__(message)

   class ConfigError(BCOError): ...
   class PlatformError(BCOError): ...
   class PipelineError(BCOError): ...
   class AuthError(BCOError): ...
   class EvaluationError(BCOError): ...
   ```

2. 定义统一返回格式：

   ```python
   @dataclass
   class Result:
       ok: bool
       data: Any = None
       error: str | None = None
       code: str | None = None
   ```

3. 逐步替换各模块的错误返回：
   - `agent/tools.py`: 空列表 → `Result(ok=False, error="...", code="NOT_FOUND")`
   - `mcp/tools.py`: `{"error": ...}` → `Result(ok=False, error=..., code=...)`
   - `web/server.py`: 统一用 `Result` 构造响应

4. Web Server 添加全局异常处理器：

   ```python
   @app.exception_handler(BCOError)
   async def bco_error_handler(request, exc):
       return JSONResponse({"ok": False, "error": exc.message, "code": exc.code}, status_code=400)
   ```

**验证**: `uv run pytest tests/ -v`

---

### 2.2 单例模式改进

**文件**: `src/boss_career_ops/config/singleton.py`, 各使用单例的模块

**修改逻辑**:

1. **统一 Endpoints 单例**: 将 `boss/api/endpoints.py` 的手动 `__new__` 单例改为使用 `SingletonMeta`

2. **添加 reload_instance 类方法**（见 1.4）

3. **SingletonMeta.__call__ 添加参数变更检测**:

   ```python
   def __call__(mcs, *args, **kwargs):
       with mcs._lock:
           cls = super().__call__
           if cls not in mcs._instances:
               mcs._instances[cls] = cls(*args, **kwargs)
           else:
               instance = mcs._instances[cls]
               if args or kwargs:
                   import warnings
                   warnings.warn(
                       f"{cls.__name__} 单例已初始化，传入的参数将被忽略。"
                       f"如需重新初始化，请调用 {cls.__name__}.reload_instance()",
                       stacklevel=2
                   )
           return mcs._instances[cls]
   ```

4. **长期方向**: 对 Settings、Thresholds 考虑使用依赖注入容器（如 `python-dependency-injector`），在 CLI 入口组装依赖，通过参数传递而非全局单例

**验证**: `uv run pytest tests/test_singleton_deadlock.py tests/test_config.py -v`

---

### 2.3 Web API / Bridge / MCP 认证

**文件**: `src/boss_career_ops/web/server.py`, `src/boss_career_ops/bridge/daemon.py`, `src/boss_career_ops/mcp/server.py`

**修改逻辑**:

1. **Web API 认证**:
   - 添加 `API_KEY` 环境变量支持（`BCO_WEB_API_KEY`）
   - 添加 FastAPI 中间件校验 `Authorization: Bearer <key>` 头
   - 读操作（GET）可免认证，写操作（打招呼/投递/修改配置）必须认证
   - 未设置 `BCO_WEB_API_KEY` 时保持当前行为（仅本地访问），但启动时打印警告

2. **Bridge Daemon 认证**:
   - WebSocket 连接时校验 `token` 查询参数
   - Token 从 `$BCO_HOME/bridge_token` 读取，Daemon 启动时自动生成
   - BridgeClient 连接时携带 token

3. **MCP Server**: MCP 协议本身通过 stdio 通信，安全性由宿主进程保证，无需额外认证

**验证**: `uv run pytest tests/test_web_server.py tests/test_bridge_daemon.py -v`

---

### 2.4 BossClient 性能优化

**文件**: `src/boss_career_ops/boss/api/client.py`

**修改逻辑**:

1. **持久化 httpx.Client**:

   ```python
   class BossClient(metaclass=SingletonMeta):
       def __init__(self):
           self._http_client: httpx.Client | None = None

       def _get_http_client(self) -> httpx.Client:
           if self._http_client is None:
               self._http_client = httpx.Client(
                   timeout=30.0,
                   follow_redirects=False,
                   proxy=os.environ.get("HTTPS_PROXY"),
               )
           return self._http_client

       def close(self):
           if self._http_client:
               self._http_client.close()
               self._http_client = None
   ```

2. **拆分 request() God Method**:
   - `_try_http_request()` — 执行单次 HTTP 请求
   - `_handle_rate_limit()` — 检测限流并退避
   - `_handle_risk_block()` — 检测风控并触发浏览器降级
   - `_request_via_browser()` — 拆分为 `_browser_get()` 和 `_browser_post()`

3. **_gaussian_delay() 改为非阻塞**: 使用 `asyncio.sleep()` 替代 `time.sleep()`，或提供异步版本

**验证**: `uv run pytest tests/test_client_improvements.py tests/test_channel_architecture.py -v`

---

### 2.5 PipelineManager 性能优化

**文件**: `src/boss_career_ops/pipeline/manager.py`

**修改逻辑**:

1. **添加数据库索引**:

   ```python
   # _init_db() 中添加
   self._conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline(stage)")
   self._conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_updated ON pipeline(updated_at)")
   self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_results_job_task ON ai_results(job_id, task_type)")
   ```

2. **批量 commit 上下文管理器**:

   ```python
   @contextmanager
   def batch_commit(self):
       """批量操作时延迟 commit，提升性能"""
       self._batch_mode = True
       try:
           yield
           self._conn.commit()
       finally:
           self._batch_mode = False

   # upsert_job / batch_add_jobs 中:
   # if not self._batch_mode: self._conn.commit()
   ```

3. **消除列名硬编码重复**: 提取为类常量

   ```python
   _PIPELINE_COLS = ["job_id", "job_name", "company_name", "stage", ...]
   _AI_RESULT_COLS = ["id", "job_id", "task_type", "result_data", ...]
   ```

4. **agent/tools.py 共享 PipelineManager 实例**: 在 agent 工具函数中使用模块级 `_pm` 实例而非每次 `with PipelineManager() as pm`

**验证**: `uv run pytest tests/test_pipeline_manager.py -v`

---

### 2.6 Agent 模块测试补充

**文件**: `tests/test_agent_graph.py`, `tests/test_agent_nodes.py`（新建）

**修改逻辑**:

1. **修复 test_agent_graph.py 的 mock 反模式**: 不再 mock `build_career_agent` 本身，而是 mock 底层依赖（LLM、PipelineManager），实际编译并执行 StateGraph

2. **新增集成测试**:

   ```python
   # test_agent_graph.py
   def test_graph_compiles_and_executes():
       """验证 StateGraph 编译成功且可执行"""
       graph = build_career_agent()
       result = graph.invoke({"messages": [...], "intent": "search", ...})
       assert "messages" in result

   def test_resume_apply_chain():
       """验证 resume+apply intent 执行两个节点"""
       graph = build_career_agent()
       result = graph.invoke({"messages": [...], "intent": "resume+apply", ...})
       # 验证 resume 和 apply 都被执行

   def test_multi_step_orchestration():
       """验证搜索→评估的多步编排"""
       graph = build_career_agent()
       result = graph.invoke({"messages": [...], "intent": "search", ...})
       # 验证 orchestrator 在 search 后路由到 evaluate
   ```

3. **为每个 Agent 节点补充行为测试**: 每个节点至少 5 个用例（happy path + 边界 + 异常 fallback）

**验证**: `uv run pytest tests/test_agent_graph.py tests/test_agent_*.py -v`

---

### 2.7 MCP 模块测试补充

**文件**: `tests/test_mcp_tools.py`, `tests/test_mcp_resources.py`

**修改逻辑**:

1. 为 9 个 MCP Tool 各编写至少 1 个 happy path 测试
2. 为 3 个 MCP Resource 各编写读取测试
3. 验证 MCP tool handler 调用了 `agent/tools.py` 中的函数（而非直接调用底层模块）
4. 验证 `evaluate_job` 调用后数据持久化到 `ai_results` 表

**验证**: `uv run pytest tests/test_mcp_tools.py tests/test_mcp_resources.py -v`

---

### 2.8 Prompt 注入防护

**文件**: `src/boss_career_ops/agent/prompts.py`

**修改逻辑**:

1. **替换 str.format() 为 string.Template**:

   ```python
   from string import Template

   # 原来: EVALUATE_PROMPT.format(profile=profile, jd=jd, ...)
   # 改为:
   EVALUATE_PROMPT = Template("""
   你是求职评估专家...
   用户画像: $profile
   职位描述: $jd
   ...
   """)

   prompt = EVALUATE_PROMPT.substitute(profile=profile, jd=jd, ...)
   ```

2. **对用户可控输入做基本清洗**: 移除/转义可能的指令注入模式（如"忽略以上指令"、"ignore previous instructions"）

3. **评分权重从 dimensions.py 动态生成**:

   ```python
   from boss_career_ops.evaluator.dimensions import DIMENSION_WEIGHTS

   weight_desc = "、".join(f"{d.label}({int(w*100)}%)" for d, w in DIMENSION_WEIGHTS)
   prompt = EVALUATE_PROMPT.substitute(..., weight_description=weight_desc)
   ```

**验证**: `uv run pytest tests/test_agent_evaluate.py -v`

---

### 2.9 私有函数公开与重复代码消除

**文件**: `src/boss_career_ops/platform/field_mapper.py`, `src/boss_career_ops/evaluator/engine.py`, `src/boss_career_ops/rag/indexer.py`, `src/boss_career_ops/evaluator/scorer.py`, `src/boss_career_ops/resume/generator.py`

**修改逻辑**:

1. **`_parse_salary()` → `parse_salary()`**: 重命名为公开函数，更新所有调用方

2. **skills 字段解析提取为共享函数**:

   ```python
   # platform/field_mapper.py
   def normalize_skills(skills_raw) -> list[str]:
       if isinstance(skills_raw, str):
           return [s.strip() for s in skills_raw.split(",") if s.strip()]
       elif isinstance(skills_raw, list):
           return [str(s).strip() for s in skills_raw if s]
       return []
   ```

   indexer.py 和 field_mapper.py 统一调用此函数

3. **合并 `grade_label()` 和 `get_recommendation()`**: 保留 `get_recommendation()`，`grade_label()` 改为调用它

4. **resume/generator.py 使用归一化字段名**: 将 `job.get("jobName")` 改为 `job.get("job_name")`，与 `Job.normalize()` 对齐

5. **JD 文本提取统一**: engine.py 和 generator.py 共享一个 `_extract_jd_text(job)` 函数

**验证**: `uv run pytest tests/test_evaluator_engine.py tests/test_field_mapper.py tests/test_resume.py -v`

---

### 2.10 同步/异步混用修复

**文件**: `src/boss_career_ops/bridge/client.py`, `src/boss_career_ops/web/server.py`

**修改逻辑**:

1. **BridgeClient 提供双接口**:

   ```python
   class BridgeClient:
       async def send_command_async(self, command): ...

       def send_command(self, command):
           """同步接口，自动检测事件循环"""
           try:
               loop = asyncio.get_running_loop()
           except RuntimeError:
               loop = None
           if loop and loop.is_running():
               # 在已有事件循环中，使用 run_in_executor
               import concurrent.futures
               with concurrent.futures.ThreadPoolExecutor() as pool:
                   return loop.run_in_executor(pool, lambda: asyncio.run(self.send_command_async(command)))
           else:
               return asyncio.run(self.send_command_async(command))
   ```

2. **Web Server 端点改为 async def**: 所有 I/O 操作（PipelineManager、BossClient）使用 `asyncio.to_thread()` 包装

**验证**: `uv run pytest tests/test_bridge_client.py tests/test_web_server.py -v`

---

## 三、P2 — 排期修复（依赖 / 配置 / 代码质量）

### 3.1 冗余依赖清理

**修改逻辑**:

1. **统一 patchright**: `resume/pdf_engine.py` 中 `from playwright.async_api import async_playwright` 改为 `from patchright.async_api import async_playwright`，移除 `playwright` 依赖
2. **Bridge 迁移到 httpx**: `bridge/client.py` 和 `bridge/daemon.py` 中 `aiohttp` 替换为 `httpx.AsyncClient`，移除 `aiohttp` 依赖
3. **FastAPI 可选化**: 在 `pyproject.toml` 中添加可选依赖组：

   ```toml
   [project.optional-dependencies]
   web = ["fastapi>=0.115", "uvicorn>=0.34"]
   ```

   CLI 核心不依赖 FastAPI，`bco web` 命令启动时检查依赖

---

### 3.2 版本约束收紧

**修改逻辑**:

```toml
# pyproject.toml
dependencies = [
    # ...
    "langchain>=0.3,<0.4",
    "langgraph>=0.2,<0.3",
    "langchain-openai>=0.2,<0.3",
    "chromadb>=0.5,<0.6",
    # ...
]
```

CI 中添加 `uv audit` 或 `pip-audit` 安全审计步骤。

---

### 3.3 配置验证

**文件**: `src/boss_career_ops/config/settings.py`, `src/boss_career_ops/config/thresholds.py`

**修改逻辑**:

1. **Profile 字段校验**:

   ```python
   def _load_profile(self, path):
       data = yaml.safe_load(f.read()) or {}
       profile = Profile(
           experience_years=max(0, int(data.get("experience_years", 0))),
           ...
       )
       if profile.expected_salary.max > 0 and profile.expected_salary.min > profile.expected_salary.max:
           raise ConfigError("期望薪资下限不能高于上限", code="INVALID_SALARY_RANGE")
       return profile
   ```

2. **Thresholds 值域校验**:

   ```python
   # auto_greet_threshold: [0, 5]
   # request_delay_min: [0.5, 60]
   # request_delay_max: >= request_delay_min
   # batch_greet_max: [1, 100]
   # retry_max_attempts: [1, 10]
   ```

3. **SalaryExpectation 默认值**: `min=0, max=0` 改为 `min=None, max=None`，区分"未设置"和"零薪资"

---

### 3.4 PROVIDER_DEFAULTS 统一

**文件**: `src/boss_career_ops/agent/llm.py`

**修改逻辑**:

1. 删除 `PROVIDER_DEFAULTS` 硬编码字典
2. `get_llm()` 从 `llm_providers.yml` 读取默认 base_url 和 model
3. 补全 `llm_providers.yml` 中的 TODO 字段（至少补全 `base_url` 和 `default_model`）

---

### 3.5 conftest.py fixture 提取

**文件**: `tests/conftest.py`

**修改逻辑**:

1. 提取 `_make_engine()` 为 `evaluator_engine` fixture
2. 提取 `mock_pm` 为 `pipeline_manager` fixture
3. 添加全局 `autouse` fixture 清理 `SingletonMeta._instances`（替代各文件自行清理）
4. 添加 `mock_adapter` fixture 供 agent/mcp 测试使用

---

### 3.6 SKILL_SYNONYMS 外置

**文件**: `src/boss_career_ops/evaluator/engine.py`

**修改逻辑**:

1. 将 `SKILL_SYNONYMS` 字典迁移到 `src/boss_career_ops/data/skill_synonyms.yml`
2. `EvaluationEngine.__init__` 中加载 YAML
3. 支持用户自定义同义词：合并 `$BCO_HOME/config/skill_synonyms.yml`

---

### 3.7 Bridge Daemon 改进

**文件**: `src/boss_career_ops/bridge/daemon.py`

**修改逻辑**:

1. `_process_command()` 的 if/elif 链改为命令注册表模式：

   ```python
   _command_handlers = {}

   @classmethod
   def register_handler(cls, command_type: CommandType):
       def decorator(func):
           cls._command_handlers[command_type] = func
           return func
       return decorator
   ```

2. 添加 `_pending_results` 超时清理机制：定期扫描并取消超时 future
3. 超时时间改为可配置（从 Thresholds 读取）

---

### 3.8 RAG 改进

**文件**: `src/boss_career_ops/rag/retriever.py`, `src/boss_career_ops/rag/chunker.py`, `src/boss_career_ops/rag/vector_store.py`

**修改逻辑**:

1. `get_skill_market_demand()` 改为批量查询：构造 OR 查询条件，单次向量搜索
2. `chunk_jd()` 添加长度检查：超过 embedding 模型 token 限制时按段落切分
3. `add_jd()` 复用 `add_jd_batch()`：单条插入调用 `add_jd_batch([doc])`
4. `search_jd()` 降级时打印 warning 而非静默丢失过滤条件

---

## 四、实施路线图

```
Phase 1 (P0 — 立即修复)
├── 1.1 评分引擎运算符 Bug
├── 1.2 Agent 图编排逻辑缺陷
├── 1.3 MCP Tools 持久化修复
└── 1.4 Web Server 架构违规修复

Phase 2 (P1 — 下一迭代)
├── 2.1 错误处理统一化
├── 2.2 单例模式改进
├── 2.3 API 认证
├── 2.4 BossClient 性能优化
├── 2.5 PipelineManager 性能优化
├── 2.6 Agent 测试补充
├── 2.7 MCP 测试补充
├── 2.8 Prompt 注入防护
├── 2.9 重复代码消除
└── 2.10 同步/异步修复

Phase 3 (P2 — 排期)
├── 3.1 冗余依赖清理
├── 3.2 版本约束收紧
├── 3.3 配置验证
├── 3.4 PROVIDER_DEFAULTS 统一
├── 3.5 conftest fixture 提取
├── 3.6 SKILL_SYNONYMS 外置
├── 3.7 Bridge Daemon 改进
└── 3.8 RAG 改进
```

---

## 五、修改约束

- 每个修改项必须编写最小测试用例并通过 `uv run pytest`
- 排查 bug 时先找根因再写测试验证，禁止直接改代码
- 修改筛选编码或 API 端点时务必对照当前 Web API 验证
- 所有影响工作流的代码改动必须同步更新 CLAUDE.md
- 代码注释使用中文，命令名和参数名使用英文
