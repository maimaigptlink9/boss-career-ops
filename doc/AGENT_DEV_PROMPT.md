# boss-career-ops Agent 核心系统开发 Prompt

> 目标：将现有 CLI 自动化工具升级为真正的 AI Agent 系统，使其同时满足「求职实用」和「面试证明 Agent 开发能力」两个目标。
> 面试证明优先级：LangGraph 多Agent编排 > RAG知识库 > MCP协议 > LLM简历改写

---

## 一、项目现状

已有能力：
- BOSS直聘 API Client（限流/重试/浏览器降级/风控处理）
- Pipeline Manager（SQLite + 6阶段流水线：发现→评估→投递→沟通→面试→offer）
- 规则评估引擎（5维度加权评分：匹配度/薪资/地点/发展/团队）
- 简历生成（关键词注入 + PDF，但只是"贴词"不是"改写"）
- Agent I/O 接口（agent-evaluate / agent-save，只是数据读写，不是真正的Agent）
- CLI 20+命令

核心缺失：
- 无 LangChain/LangGraph
- 无 RAG（向量检索+知识库）
- 无 MCP 协议
- 无 Function Calling
- 无多Agent协作
- 无 LLM 驱动决策（评估是规则引擎，简历改写是硬编码）
- 无 Prompt Engineering

---

## 二、系统一：LangGraph 多Agent编排（面试证明权重 ★★★★★）

### 为什么最关键
面试官判断你是否真正做过Agent开发，第一个问题就是"你的Agent架构是怎么设计的"。LangGraph是目前最主流的Agent编排框架，JD中出现频率最高。能讲清楚State/Node/Edge/Conditional Edge的设计决策，比任何项目描述都有说服力。

### 架构设计

```
                        ┌─────────────┐
                        │  User Input │
                        └──────┬──────┘
                               ↓
                        ┌─────────────┐
                        │  Orchestrator│  ← LangGraph StateGraph 入口
                        └──────┬──────┘
                               ↓
                    ┌──────────────────────┐
                    │  Conditional Router   │  ← 根据 intent 路由
                    └──┬───┬───┬───┬───────┘
                       ↓   ↓   ↓   ↓
                ┌──────┐┌──────┐┌──────┐┌──────┐
                │Search││Eval  ││Resume││Apply │
                │Agent ││Agent ││Agent ││Agent │
                └──┬───┘└──┬───┘└──┬───┘└──┬───┘
                   ↓       ↓       ↓       ↓
                ┌──────────────────────────────┐
                │       Shared State           │
                │  (TypedDict + Annotated)     │
                └──────────────────────────────┘
                   ↓       ↓       ↓       ↓
                ┌──────────────────────────────┐
                │       Tool Layer (MCP)       │
                │  search | evaluate | greet   │
                │  resume | apply | chat       │
                └──────────────────────────────┘
```

### 文件结构

```
src/boss_career_ops/agent/
├── __init__.py
├── graph.py              # LangGraph StateGraph 定义 + 编译
├── state.py              # 共享状态 TypedDict
├── prompts.py            # 所有 Prompt 模板
├── tools.py              # 现有，保留为工具层
├── nodes/
│   ├── __init__.py
│   ├── orchestrator.py   # 路由节点：分析用户意图，决定走哪个Agent
│   ├── search.py         # 搜索Agent：多关键词策略 + 结果去重
│   ├── evaluate.py       # 评估Agent：LLM语义分析替代规则匹配
│   ├── resume.py         # 简历Agent：LLM改写叙事
│   ├── apply.py          # 投递Agent：打招呼语生成 + 投递决策
│   └── gap_analysis.py   # 技能差距分析Agent
└── conditions.py         # Conditional Edge 的路由逻辑
```

### 开发 Prompt

```
你是一个 Python Agent 开发专家。请基于以下要求，为 boss-career-ops 项目实现 LangGraph 多Agent编排系统。

## 技术约束
- Python 3.12+
- 使用 langgraph >= 0.2（StateGraph, Node, Edge, ConditionalEdge）
- 使用 langchain >= 0.3（ChatPromptTemplate, Runnable）
- 使用 langchain-openai（ChatOpenAI）作为 LLM Provider
- 所有 LLM 调用必须支持 fallback（OpenAI 不可用时降级到本地模型或规则引擎）
- 与现有 Pipeline Manager（SQLite）集成，不替换，只增强

## State 定义（state.py）

使用 TypedDict + Annotated 定义共享状态：

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]       # 对话历史
    intent: str                                    # 用户意图：search/evaluate/resume/apply/gap_analysis
    job_ids: list[str]                             # 当前处理的职位ID列表
    current_job_id: str                            # 当前聚焦的职位
    job_details: dict[str, dict]                   # job_id → 职位详情缓存
    evaluation_results: dict[str, dict]            # job_id → 评估结果
    resume_versions: dict[str, str]                # job_id → 定制简历Markdown
    skill_gaps: dict                               # 技能差距分析结果
    rag_context: str                               # RAG检索到的上下文
    errors: list[str]                              # 错误收集
    next_action: str                               # 下一步行动提示
```

## Graph 定义（graph.py）

```python
from langgraph.graph import StateGraph, END
from boss_career_ops.agent.state import AgentState
from boss_career_ops.agent.nodes import orchestrator, search, evaluate, resume, apply, gap_analysis
from boss_career_ops.agent.conditions import route_by_intent

def build_career_agent() -> CompiledGraph:
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("orchestrator", orchestrator.run)
    graph.add_node("search", search.run)
    graph.add_node("evaluate", evaluate.run)
    graph.add_node("resume", resume.run)
    graph.add_node("apply", apply.run)
    graph.add_node("gap_analysis", gap_analysis.run)

    # 定义边
    graph.set_entry_point("orchestrator")
    graph.add_conditional_edges("orchestrator", route_by_intent, {
        "search": "search",
        "evaluate": "evaluate",
        "resume": "resume",
        "apply": "apply",
        "gap_analysis": "gap_analysis",
    })

    # 各Agent执行完后回到orchestrator（支持多轮对话）
    graph.add_edge("search", END)         # 搜索完结束，等用户下一步
    graph.add_edge("evaluate", END)       # 评估完结束
    graph.add_edge("resume", END)         # 简历生成完结束
    graph.add_edge("apply", END)          # 投递完结束
    graph.add_edge("gap_analysis", END)   # 差距分析完结束

    return graph.compile()
```

## 各节点实现要求

### orchestrator.py
- 输入：用户自然语言指令
- 使用 LLM 分析意图，输出 intent 字段
- 支持的意图：search（搜索职位）、evaluate（评估匹配度）、resume（生成定制简历）、apply（投递+打招呼）、gap_analysis（技能差距分析）
- 如果用户说"帮我找深圳的Agent岗位"，识别为 search，提取参数 city=深圳, keyword=Agent
- 如果用户说"这个岗位我匹配吗"，识别为 evaluate
- 如果用户说"帮我改简历投这个岗"，识别为 resume + apply 的组合

### search.py（搜索Agent）
- 调用现有 boss_career_ops.platform.registry.get_active_adapter().search()
- 增强点：LLM 生成多关键词组合策略（解决中文关键词搜索支持差的问题）
  - 输入用户目标 → LLM 生成多组英文搜索词 → 并行搜索 → 去重合并
- 搜索结果写入 Pipeline Manager（复用现有 batch_add_jobs）
- 输出：结构化职位列表 + 初步匹配建议

### evaluate.py（评估Agent）
- 替代现有规则引擎 EvaluationEngine，改为 LLM 语义评估
- 保留规则引擎作为 fallback（LLM 不可用时降级）
- LLM 评估维度与现有5维度对齐：匹配度/薪资/地点/发展/团队
- 关键增强：LLM 能理解"数据分析经验"和"数据驱动Agent开发"的关联性（规则引擎做不到）
- 评估结果通过 write_evaluation() 写入 Pipeline

### resume.py（简历Agent）— 详见系统四
- LLM 驱动的简历叙事改写
- 不是贴关键词，而是重写项目描述的叙事角度

### apply.py（投递Agent）
- LLM 生成针对性打招呼语（当前 greet 是固定模板）
- 根据JD和简历内容，生成个性化的"为什么我适合这个岗位"的开场白
- 调用现有 adapter.greet() + adapter.apply()

### gap_analysis.py（技能差距分析Agent）
- 输入：profile + 目标JD列表
- LLM 分析：当前技能 vs JD要求的差距
- 输出：缺失技能 + 优先级排序 + 学习建议
- 结果写入 ai_results 表（task_type = "gap_analysis"）

## conditions.py
- route_by_intent(state: AgentState) -> str
- 根据 state["intent"] 返回对应节点名
- 支持组合意图（如 resume+apply）时先走 resume 再走 apply

## CLI 集成
- 新增命令 `bco agent "帮我找深圳的Agent岗位并评估匹配度"`
- 在 main.py 中注册：
```python
@cli.command("agent")
@click.argument("query", nargs=-1)
@click.option("--interactive", is_flag=True, help="交互模式")
def agent_cmd(query, interactive):
    """AI Agent 对话式求职助手"""
    from boss_career_ops.commands.agent_cmd import run_agent
    run_agent(" ".join(query), interactive=interactive)
```

## LLM 配置
- 从环境变量读取：BCO_LLM_PROVIDER（openai/deepseek/local）、BCO_LLM_API_KEY、BCO_LLM_BASE_URL、BCO_LLM_MODEL
- 默认使用 deepseek-chat（性价比高，中文能力强）
- 支持 OpenAI 兼容接口（DeepSeek/月之暗面/本地Ollama都兼容）

## 面试话术要点（写代码时注意体现）
1. "我选择 LangGraph 而不是纯 LangChain Agent，是因为需要精确控制Agent流转逻辑，Conditional Edge 让路由可预测可调试"
2. "State 用 TypedDict 而不是 dataclass，是因为 LangGraph 的消息追加需要 Annotated[list, add_messages]"
3. "保留了规则引擎作为 fallback，因为 LLM 有延迟和成本，生产环境需要确定性兜底"
4. "orchestrator 模式而非纯链式，是因为求职流程不是线性的，用户可能随时跳到任意阶段"
```

---

## 三、系统二：RAG 知识库（面试证明权重 ★★★★★）

### 为什么最关键
RAG 是 Agent 的"记忆"和"知识"层。80%的JD要求RAG经验。面试官会问"你的RAG是怎么做的？向量模型选的什么？chunk策略是什么？检索后怎么重排？"。能回答这些问题，RAG能力就证明了。

### 架构设计

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  JD 数据源   │     │  简历模板库  │     │  面试经验库  │
│ (Pipeline DB)│     │ (成功简历集) │     │ (用户反馈)   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       ↓                    ↓                    ↓
┌──────────────────────────────────────────────────────┐
│                    Indexer                            │
│  1. 读取数据 → 2. 切分Chunk → 3. Embedding → 4. 存储 │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│              ChromaDB (本地向量库)                     │
│  Collection: jd_knowledge                           │
│  Collection: resume_templates                       │
│  Collection: interview_experience                   │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│                   Retriever                          │
│  1. Query Embedding → 2. 相似度检索 → 3. MMR重排     │
│  4. 元数据过滤（城市/薪资/行业）                       │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│              Agent 消费层                             │
│  EvaluateAgent: 语义匹配（替代关键词匹配）             │
│  ResumeAgent: 检索相似JD的成功简历模板                 │
│  InterviewAgent: 检索该公司/行业的面试经验             │
└──────────────────────────────────────────────────────┘
```

### 文件结构

```
src/boss_career_ops/rag/
├── __init__.py
├── embedder.py          # Embedding 模型封装
├── vector_store.py      # ChromaDB 封装
├── indexer.py           # 数据索引构建
├── retriever.py         # 检索器
├── chunker.py           # 文本切分策略
└── schemas.py           # 文档元数据Schema
```

### 开发 Prompt

```
你是一个 RAG 系统开发专家。请为 boss-career-ops 项目实现 RAG 知识库。

## 技术约束
- 使用 chromadb >= 0.5 作为向量数据库（本地持久化，无需外部服务）
- Embedding 模型：优先使用 chromadb 默认的 all-MiniLM-L6-v2（本地运行，无需API Key）
  - 可选升级：通过 BCO_EMBEDDING_PROVIDER 配置使用 OpenAI embedding
- 与现有 Pipeline Manager（SQLite）集成，JD数据从 pipeline 表读取
- 向量库存储路径：~/.bco/chroma_db

## schemas.py — 文档元数据定义

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class JDDocument:
    doc_id: str                    # job_id
    content: str                   # JD全文（职位名+技能+描述）
    job_name: str                  # 职位名
    company_name: str              # 公司名
    city: str                      # 城市
    salary_min: int                # 薪资下限
    salary_max: int                # 薪资上限
    skills: list[str]              # 技能标签
    industry: str                  # 行业
    score: float                   # 评估分数（如有）
    grade: str                     # 评估等级（如有）

@dataclass
class ResumeTemplate:
    doc_id: str                    # resume_{job_id}
    content: str                   # 简历Markdown全文
    job_name: str                  # 目标职位名
    company_name: str              # 目标公司
    result: str                    # 投递结果：replied/rejected/interviewed/offer
    keywords: list[str]            # 关键词标签

@dataclass
class InterviewExperience:
    doc_id: str                    # interview_{job_id}
    content: str                   # 面试准备/反馈全文
    company_name: str              # 公司名
    job_name: str                  # 职位名
    questions: list[str]           # 面试题
    result: str                    # 结果：passed/failed/pending
```

## chunker.py — 文本切分策略

JD 文档切分策略（关键：不能把一个JD拆散）：
- 每个 JD 作为一个 chunk（JD通常不超过2000字，在embedding模型上下文内）
- 元数据跟随 chunk 存储
- 不使用 RecursiveCharacterTextSplitter，因为 JD 是结构化短文本

简历模板切分策略：
- 按章节切分：基本信息/技能/工作经历/项目经历/教育背景
- 每个章节作为独立 chunk，保留章节名作为元数据
- 这样检索时可以只检索"项目经历"章节，用于简历改写参考

## embedder.py — Embedding 封装

```python
class Embedder:
    def __init__(self, provider: str = "local"):
        """
        provider: "local" (all-MiniLM-L6-v2) | "openai" (text-embedding-3-small)
        """
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...
```

## vector_store.py — ChromaDB 封装

```python
class VectorStore:
    def __init__(self, persist_dir: str = "~/.bco/chroma_db"):
        ...

    def add_jd(self, doc: JDDocument) -> None:
        """添加JD到 jd_knowledge collection"""

    def add_jd_batch(self, docs: list[JDDocument]) -> None:
        """批量添加JD"""

    def add_resume_template(self, doc: ResumeTemplate) -> None:
        """添加简历模板"""

    def add_interview_experience(self, doc: InterviewExperience) -> None:
        """添加面试经验"""

    def search_jd(self, query: str, n: int = 10, filters: dict | None = None) -> list[dict]:
        """语义搜索JD，支持元数据过滤（城市/薪资/行业）"""

    def search_resume(self, query: str, n: int = 5, filters: dict | None = None) -> list[dict]:
        """搜索相似简历模板"""

    def search_interview(self, query: str, n: int = 5) -> list[dict]:
        """搜索面试经验"""

    def delete_jd(self, job_id: str) -> None:
        """删除指定JD"""
```

## indexer.py — 索引构建

```python
class Indexer:
    def __init__(self):
        self._pipeline = PipelineManager()
        self._store = VectorStore()
        self._embedder = Embedder()

    def index_from_pipeline(self) -> int:
        """从 Pipeline DB 读取所有JD，构建向量索引。返回索引文档数。"""

    def index_single_jd(self, job_id: str) -> None:
        """索引单个JD（新发现时调用）"""

    def index_resume_result(self, job_id: str, resume_md: str, result: str) -> None:
        """索引简历生成结果"""

    def reindex_all(self) -> int:
        """全量重建索引。返回索引文档数。"""
```

## retriever.py — 检索器

```python
class Retriever:
    def __init__(self):
        self._store = VectorStore()

    def find_similar_jds(self, query: str, n: int = 10, city: str = "", salary_min: int = 0) -> list[dict]:
        """语义搜索相似JD。用于：评估Agent理解岗位相似性。"""

    def find_matching_resumes(self, jd_text: str, n: int = 5) -> list[dict]:
        """根据JD内容检索最相似的成功简历模板。用于：简历Agent学习叙事方式。"""

    def find_interview_tips(self, company: str, job_name: str, n: int = 5) -> list[dict]:
        """检索该公司/职位的面试经验。用于：面试Agent生成准备方案。"""

    def get_skill_market_demand(self, skills: list[str]) -> dict[str, int]:
        """分析技能在市场中的需求度。用于：技能差距Agent判断优先级。"""
        # 实现思路：对每个skill做语义搜索，统计匹配JD数量
```

## CLI 集成

```python
@cli.command("rag-index")
@click.option("--reindex", is_flag=True, help="全量重建索引")
def rag_index(reindex):
    """构建/更新 RAG 知识库索引"""
    from boss_career_ops.commands.rag import run_rag_index
    run_rag_index(reindex=reindex)

@cli.command("rag-search")
@click.argument("query")
@click.option("--collection", default="jd", type=click.Choice(["jd", "resume", "interview"]))
@click.option("--top-k", default=10, type=int)
def rag_search(query, collection, top_k):
    """RAG 语义搜索"""
    from boss_career_ops.commands.rag import run_rag_search
    run_rag_search(query, collection, top_k)
```

## 面试话术要点
1. "我选 ChromaDB 而不是 Pinecone/Weaviate，因为求职场景数据量小（百级JD），本地持久化足够，不需要分布式向量库的运维成本"
2. "JD不切分，整个作为一个chunk，因为JD是结构化短文本，切分会破坏语义完整性"
3. "简历模板按章节切分，是因为简历改写时需要参考特定章节的叙事方式，不需要全文"
4. "检索用 MMR（Maximal Marginal Relevance）而不是纯相似度，避免返回内容高度重复的结果"
5. "元数据过滤在 ChromaDB 层完成，先过滤再检索，避免无关文档浪费 token"
```

---

## 四、系统三：MCP Server（面试证明权重 ★★★★★）

### 为什么最关键
MCP 是 Anthropic 提出的 Agent 工具调用标准协议，2024年底发布后迅速成为行业趋势。JD中越来越多提到MCP。能讲清楚 MCP 的 Server/Client/Tool/Resource 模型，说明你紧跟前沿。而且实现成本低——你已有20+命令，只需包一层MCP协议。

### 架构设计

```
┌──────────────────────────────────────┐
│          MCP Client (Claude/其他)     │
│  通过 stdio/SSE 连接 MCP Server      │
└──────────────┬───────────────────────┘
               ↓ MCP Protocol (JSON-RPC)
┌──────────────────────────────────────┐
│          MCP Server (本项目)          │
│                                      │
│  Tools:                              │
│  ├── search_jobs(keyword, city)      │
│  ├── evaluate_job(job_id)            │
│  ├── generate_resume(job_id)         │
│  ├── greet_recruiter(sid, jid)       │
│  ├── apply_job(sid, jid)             │
│  ├── get_pipeline(stage)             │
│  ├── get_job_detail(job_id)          │
│  ├── analyze_skill_gap()             │
│  └── prepare_interview(job_id)       │
│                                      │
│  Resources:                          │
│  ├── bco://profile                   │
│  ├── bco://cv                        │
│  └── bco://pipeline/{stage}          │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│     现有 boss-career-ops 能力层       │
│  BossClient | PipelineManager |      │
│  EvaluationEngine | ResumeGenerator  │
└──────────────────────────────────────┘
```

### 文件结构

```
src/boss_career_ops/mcp/
├── __init__.py
├── server.py            # MCP Server 主入口
├── tools.py             # Tool 定义和注册
└── resources.py         # Resource 定义和注册
```

### 开发 Prompt

```
你是一个 MCP 协议开发专家。请为 boss-career-ops 项目实现 MCP Server。

## 技术约束
- 使用 mcp >= 1.0 Python SDK（from mcp.server import Server）
- 传输方式：stdio（作为子进程被 MCP Client 启动）
- 与现有代码集成，不重复实现业务逻辑

## server.py — MCP Server 主入口

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from boss_career_ops.mcp.tools import register_tools
from boss_career_ops.mcp.resources import register_resources

app = Server("boss-career-ops")

register_tools(app)
register_resources(app)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
```

## tools.py — Tool 定义

每个 Tool 必须包含：name、description、inputSchema（JSON Schema）、handler。

```python
from mcp.server import Server
from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.resume.generator import ResumeGenerator
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.agent.tools import get_job_detail, get_profile, get_cv, list_pipeline_jobs

def register_tools(app: Server):

    @app.tool("search_jobs")
    async def search_jobs(keyword: str, city: str = "") -> str:
        """搜索BOSS直聘职位。keyword为搜索关键词，city为城市名（如'深圳'）。返回职位列表JSON。"""
        adapter = get_active_adapter()
        params = adapter.build_search_params(keyword, city)
        jobs = adapter.search(params)
        import json
        return json.dumps([j.to_dict() for j in jobs], ensure_ascii=False, indent=2)

    @app.tool("evaluate_job")
    async def evaluate_job(job_id: str) -> str:
        """评估职位匹配度。job_id为职位ID。返回5维度评估结果（匹配度/薪资/地点/发展/团队）。"""
        adapter = get_active_adapter()
        job = adapter.get_job_detail(job_id)
        if not job:
            return json.dumps({"error": "职位不存在"}, ensure_ascii=False)
        engine = EvaluationEngine()
        result = engine.evaluate(job)
        return json.dumps(result, ensure_ascii=False, indent=2)

    @app.tool("generate_resume")
    async def generate_resume(job_id: str) -> str:
        """为指定职位生成定制简历。job_id为职位ID。返回Markdown格式简历。"""
        adapter = get_active_adapter()
        job = adapter.get_job_detail(job_id)
        if not job:
            return json.dumps({"error": "职位不存在"}, ensure_ascii=False)
        job_dict = job.raw_data if job.raw_data else job.to_dict()
        generator = ResumeGenerator()
        resume_md = generator.generate(job_dict)
        return resume_md or "简历生成失败"

    @app.tool("greet_recruiter")
    async def greet_recruiter(security_id: str, job_id: str) -> str:
        """向招聘者打招呼。security_id和job_id可通过search_jobs或get_pipeline获取。"""
        adapter = get_active_adapter()
        result = adapter.greet(security_id, job_id)
        return json.dumps({"ok": result.ok, "message": result.message}, ensure_ascii=False)

    @app.tool("apply_job")
    async def apply_job(security_id: str, job_id: str) -> str:
        """投递简历。security_id和job_id可通过search_jobs或get_pipeline获取。"""
        # 调用现有 apply 逻辑
        ...

    @app.tool("get_pipeline")
    async def get_pipeline(stage: str = "") -> str:
        """获取求职流水线中的职位。stage可选：发现/评估/投递/沟通/面试/offer。不传则返回全部。"""
        jobs = list_pipeline_jobs(stage=stage or None)
        return json.dumps(jobs, ensure_ascii=False, indent=2)

    @app.tool("get_job_detail")
    async def get_job_detail_tool(job_id: str) -> str:
        """获取职位详情，包含评估结果。"""
        job = get_job_detail(job_id)
        if not job:
            return json.dumps({"error": "职位不存在"}, ensure_ascii=False)
        return json.dumps(job, ensure_ascii=False, indent=2)

    @app.tool("analyze_skill_gap")
    async def analyze_skill_gap() -> str:
        """分析当前技能与市场需求的差距。基于profile和已索引的JD数据。"""
        # 调用 gap_analysis Agent 或 RAG 检索
        ...

    @app.tool("prepare_interview")
    async def prepare_interview(job_id: str) -> str:
        """为指定职位生成面试准备方案。包含技术题预测、项目经历深挖、公司背景调研。"""
        # 调用 interview Agent
        ...
```

## resources.py — Resource 定义

```python
from mcp.server import Server
from boss_career_ops.agent.tools import get_profile, get_cv
from boss_career_ops.pipeline.manager import PipelineManager
import json

def register_resources(app: Server):

    @app.resource("bco://profile")
    async def profile_resource() -> str:
        """求职者个人档案"""
        return json.dumps(get_profile(), ensure_ascii=False, indent=2)

    @app.resource("bco://cv")
    async def cv_resource() -> str:
        """求职者简历内容"""
        return get_cv()

    @app.resource("bco://pipeline/{stage}")
    async def pipeline_resource(stage: str) -> str:
        """指定阶段的求职流水线数据"""
        with PipelineManager() as pm:
            jobs = pm.list_jobs(stage=stage)
            return json.dumps(jobs, ensure_ascii=False, indent=2)
```

## CLI 集成

```python
@cli.command("mcp-server")
def mcp_server():
    """启动 MCP Server（供 Claude Desktop 等客户端调用）"""
    import asyncio
    from boss_career_ops.mcp.server import main
    asyncio.run(main())
```

## Claude Desktop 配置示例（面试演示用）

```json
{
  "mcpServers": {
    "boss-career-ops": {
      "command": "bco",
      "args": ["mcp-server"]
    }
  }
}
```

## 面试话术要点
1. "MCP 的核心价值是标准化了Agent的工具调用接口，让不同的Agent框架可以复用同一套工具"
2. "我选 stdio 传输而不是 SSE，是因为本地场景下 stdio 更简单可靠，不需要启动HTTP服务"
3. "Tool 和 Resource 的区分：Tool 是有副作用的操作（打招呼/投递），Resource 是只读数据（档案/简历）"
4. "inputSchema 用 JSON Schema 定义，这样 MCP Client 可以自动生成参数表单"
5. "这个 MCP Server 让 Claude Desktop 直接成为我的求职助手，自然语言对话就能完成搜索→评估→投递全流程"
```

---

## 五、系统四：LLM 简历改写（面试证明权重 ★★★★）

### 为什么关键
这是你当前最迫切的实用需求，同时证明 Prompt Engineering 能力。面试官问"你的Prompt怎么设计的"，你要能讲清楚模板设计、Few-shot、Chain-of-Thought。

### 开发 Prompt

```
你是一个 Prompt Engineering 专家。请为 boss-career-ops 的简历Agent实现 LLM 驱动的简历改写。

## 核心原则
不是"贴关键词"，而是"改写叙事角度"。把7年数据分析经历翻译成Agent开发叙事。

## 文件：src/boss_career_ops/agent/nodes/resume.py

## Prompt 模板设计

### System Prompt

```
你是一个资深简历改写专家。你的任务是将求职者的原始简历，针对目标岗位的JD，进行叙事角度的改写。

改写规则：
1. 不编造不存在的经历或技能
2. 不改变事实内容（公司/时间/职责范围）
3. 只改变叙事角度：将数据分析视角的描述，改写为AI Agent开发视角
4. 保留原始简历的结构和格式
5. 每个项目经历必须体现：问题定义 → 技术方案 → 量化成果

叙事转换示例：
- "使用永宏BI制作报告" → "设计并实现数据驱动的智能决策Agent，自动化定价报告生成与分发流程"
- "对齐数据口径，负责报告中各指标公式设计" → "构建定价知识图谱与指标推理引擎，实现多维度数据的语义对齐与自动化计算"
- "从多个数据源收集仓储相关数据，利用Kettle进行数据清洗和整合" → "设计ETL Agent自动化数据采集与清洗流水线，实现多源异构数据的智能整合"
- "利用帆软report制作数据可视化报表" → "开发智能报表Agent，将数据分析能力封装为可交互的自动化报告服务"
- "向一线员工提供定价建议并监控定价执行情况" → "构建定价建议Agent，实现定价策略的自动推荐与执行监控闭环"
```

### User Prompt 模板

```
## 原始简历
{cv_content}

## 目标岗位 JD
职位名称：{job_name}
公司：{company_name}
薪资：{salary_desc}

岗位要求：
{job_requirements}

岗位职责：
{job_responsibilities}

## 技能差距分析
当前技能：{current_skills}
JD要求技能：{required_skills}
缺失技能：{missing_skills}

## 改写要求
1. 在技能部分，将JD要求且你确实掌握的技能放在前面
2. 在项目经历部分，用上述叙事转换规则改写描述
3. 在项目经历中，尽量体现与JD要求技能的关联
4. 不要删除任何项目经历，只改写描述
5. 如果JD要求某项技能且你有相关经验，在对应项目中突出体现
6. 输出完整的Markdown格式简历
```

### Few-shot 示例（嵌入 Prompt）

在 System Prompt 中加入2-3个改写前后的对比示例，让LLM理解改写风格。

## 实现代码结构

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from boss_career_ops.agent.state import AgentState
from boss_career_ops.config.settings import Settings
from boss_career_ops.rag.retriever import Retriever

RESUME_SYSTEM_PROMPT = """...(上述System Prompt)..."""

RESUME_USER_PROMPT = """...(上述User Prompt模板)..."""

async def run(state: AgentState) -> AgentState:
    settings = Settings()
    cv = settings.cv_content
    profile = settings.profile

    job_id = state.get("current_job_id", "")
    job_detail = state.get("job_details", {}).get(job_id, {})

    # RAG: 检索相似JD的成功简历模板作为参考
    retriever = Retriever()
    similar_resumes = retriever.find_matching_resumes(
        jd_text=_extract_jd_text(job_detail),
        n=3
    )
    rag_context = "\n\n".join(r["content"] for r in similar_resumes)

    # LLM 改写
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESUME_SYSTEM_PROMPT),
        ("human", RESUME_USER_PROMPT),
    ])
    chain = prompt | llm

    result = await chain.ainvoke({
        "cv_content": cv,
        "job_name": job_detail.get("job_name", ""),
        "company_name": job_detail.get("company_name", ""),
        "salary_desc": job_detail.get("salary_desc", ""),
        "job_requirements": job_detail.get("description", ""),
        "job_responsibilities": job_detail.get("description", ""),
        "current_skills": ", ".join(profile.skills),
        "required_skills": ", ".join(job_detail.get("skills", [])),
        "missing_skills": _compute_missing_skills(profile.skills, job_detail.get("skills", [])),
        "rag_context": rag_context,
    })

    # 保存结果
    from boss_career_ops.agent.tools import write_resume
    write_resume(job_id, result.content)

    state["resume_versions"][job_id] = result.content
    state["next_action"] = f"简历已生成，可使用 bco resume {job_id} --format pdf 生成PDF"
    return state
```

## 面试话术要点
1. "简历改写不是关键词堆砌，而是叙事角度转换。我设计了System Prompt定义转换规则，Few-shot示例让LLM理解风格"
2. "RAG检索相似JD的成功简历模板作为参考，让改写不只是理论推导，而是基于真实成功案例"
3. "保留了原始事实不变的原则——不编造经历，只改写视角。这是Prompt Engineering的约束设计"
4. "技能差距分析作为额外输入，让改写有针对性——重点突出与JD匹配的经验"
```

---

## 六、依赖升级汇总

在 pyproject.toml 的 dependencies 中新增：

```toml
dependencies = [
    # 现有依赖保持不变...
    "langchain>=0.3",
    "langgraph>=0.2",
    "langchain-openai>=0.2",
    "chromadb>=0.5",
    "mcp>=1.0",
]
```

---

## 七、开发顺序建议

```
Phase 1（1-2天）：LLM简历改写
  → 立即可用于求职
  → 验证 LLM 接入可行性
  → 文件：agent/nodes/resume.py + agent/prompts.py

Phase 2（2-3天）：LangGraph 多Agent编排
  → 核心架构搭建
  → 先实现 orchestrator + evaluate + resume 三个节点
  → 文件：agent/graph.py + agent/state.py + agent/nodes/*

Phase 3（1-2天）：RAG 知识库
  → 从 Pipeline DB 导入JD数据
  → 实现语义搜索
  → 文件：rag/*

Phase 4（1天）：MCP Server
  → 包装现有命令为MCP Tool
  → 文件：mcp/*

Phase 5（1天）：集成测试 + CLI命令
  → 端到端测试
  → 面试演示准备
```

---

## 八、面试演示脚本

面试时按以下顺序演示：

1. **开场**："我开发了一个AI求职Agent，用LangGraph编排4个专业Agent，通过RAG知识库做语义匹配，通过MCP协议暴露工具接口"
2. **演示MCP**：打开Claude Desktop，自然语言对话完成搜索→评估→简历→投递
3. **演示RAG**：展示语义搜索vs关键词搜索的差异（"数据分析"能匹配到"数据驱动决策"的JD）
4. **演示简历改写**：展示同一份简历针对不同JD的改写结果差异
5. **展示代码**：graph.py的StateGraph定义，讲Conditional Edge的设计决策
6. **收尾**："这个项目让我从数据分析成功转型到Agent开发，它本身就是我Agent能力的证明"
