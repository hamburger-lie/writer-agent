# Multi-Agent Writing System / 多Agent写作系统

基于 DeepSeek LLM 的多角色协作写作系统，具备自主联网搜索、独立记忆存储和自动反思能力。

## 系统架构

### 核心理念

每个子Agent拥有**独立的数据库**（SQLite + ChromaDB），数据互不共享。跨Agent的知识访问由专职的"图书管理员"Agent统一协调，确保数据隔离的同时又能实现知识流通。

### 写作流水线

```
用户输入主题
    │
    ▼
┌─────────┐    定方向、拟大纲
│  策划    │    deepseek-reasoner (R1)
└────┬────┘
     │
     ▼
┌─────────┐    自主搜索 + Crawl4AI 爬取
│  调研    │    deepseek-chat (V3)
└────┬────┘
     │
     ▼
┌─────────┐    根据大纲和素材写初稿
│  主笔    │    deepseek-chat (V3)
└────┬────┘
     │
     ▼
┌─────────┐    优化语言、文风、可读性
│  润色    │    deepseek-chat (V3)
└────┬────┘
     │
     ▼
┌─────────┐    质量审核、事实核查
│  审核    │    deepseek-reasoner (R1)
└────┬────┘
     │ 不通过 → 回到润色（最多2轮）
     │ 通过 ↓
     ▼
┌─────────┐    cibe-whitepaper 格式化输出
│  发布    │
└─────────┘
```

### 6个子Agent

| 角色 | 代号 | 模型 | 职责 |
|------|------|------|------|
| **策划** | `planner` | deepseek-reasoner (R1) | 分析主题方向、目标受众、文章结构，输出大纲和调研问题 |
| **调研** | `researcher` | deepseek-chat (V3) | 自动生成搜索关键词 → 调用搜索引擎API → Crawl4AI爬取网页 → 提取结构化素材 |
| **主笔** | `writer` | deepseek-chat (V3) | 基于大纲和素材撰写完整初稿，融合cibe-whitepaper的提示词模板 |
| **润色** | `polisher` | deepseek-chat (V3) | 优化措辞、改善行文节奏、增强可读性，保持专业性 |
| **审核** | `reviewer` | deepseek-reasoner (R1) | 检查事实准确性、逻辑连贯性、规则合规性，输出通过/不通过及修改建议 |
| **图书管理员** | `librarian` | deepseek-chat (V3) | 管理所有Agent的知识库和共享素材库，协调跨Agent知识检索 |

### 存储架构

```
data/
├── agents/                          # 每个Agent独立的数据目录
│   ├── planner/
│   │   ├── planner.db               # SQLite: 规则、历史、反思
│   │   └── chroma/                  # ChromaDB: 知识语义检索
│   ├── researcher/
│   │   ├── researcher.db
│   │   └── chroma/
│   ├── writer/
│   │   ├── writer.db
│   │   └── chroma/
│   ├── polisher/
│   │   ├── polisher.db
│   │   └── chroma/
│   ├── reviewer/
│   │   ├── reviewer.db
│   │   └── chroma/
│   └── librarian/
│       ├── librarian.db
│       └── chroma/
├── shared/                          # 图书管理员管理的共享素材库
│   └── chroma/
├── tasks/                           # 每次任务的完整输出
│   └── {task_id}/
│       ├── plan.json                # 策划输出
│       ├── research.json            # 调研素材
│       ├── draft.md                 # 初稿
│       ├── polished.md              # 润色稿
│       ├── review.json              # 审核意见
│       └── final.md                 # 终稿
└── exports/                         # 已发布文章
```

#### SQLite 表结构（每个Agent相同的schema，不同的数据）

- **rules** — 积累的写作/操作规则（来源：自动反思 or 人工反馈）
- **task_history** — 任务执行历史（输入摘要、输出摘要、耗时、token用量）
- **reflections** — 反思记录（经验教训、触发上下文、是否已晋升为规则）
- **metadata** — Agent级别的键值配置

#### ChromaDB 集合（每个Agent）

- **`{agent}_knowledge`** — Agent产出/消费的内容（按~500 token分块），支持按主题、内容类型、质量分数过滤
- **`{agent}_rules`** — 规则的语义索引（SQLite规则的镜像，用于语义检索相关规则）

#### 共享素材库

- **`shared_materials`** — 跨Agent可访问的素材库，由图书管理员统一管理写入和检索

### 跨Agent数据访问协议

1. Agent可以**直接读写**自己的SQLite和ChromaDB
2. 要访问其他Agent的数据，**必须通过图书管理员**代理
3. 只有图书管理员有权写入共享素材库
4. 流水线中，调研完成后自动将素材索引到共享库

## 两大核心功能

### 功能一：自主联网搜索

调研Agent的工作流：

```
1. 接收策划Agent的调研问题
2. 用LLM生成多组搜索关键词
3. 调用搜索引擎API（Bing/Google/Serper）获取URL列表
4. Crawl4AI并发爬取网页，提取干净的Markdown
5. LLM从爬取内容中提取关键信息、数据点
6. 整理输出结构化素材（含来源引用）
```

### 功能二：多角色协作写作

6个Agent按流水线顺序执行，每个Agent：
- 从自己的知识库中检索相关历史经验
- 加载自己积累的规则作为约束
- 执行角色职责，产出结构化输出
- 执行后自动反思，积累新经验

审核环节支持**退回重写**：如果审核不通过，润色Agent根据审核意见重新打磨，最多循环2轮。

## 记忆、检索与反思

### 记忆（Memory）

每个Agent通过独立的SQLite + ChromaDB积累经验：
- **SQLite** 存储结构化记忆：规则文本、置信度、来源、分类
- **ChromaDB** 存储语义化记忆：历史产出内容的向量嵌入，支持相似度检索

### 检索（Retrieval）

Agent执行前会进行两类检索：
- **规则检索**：从SQLite读取活跃规则，注入system prompt作为约束
- **语义检索**：用当前任务主题查询ChromaDB，获取最相关的历史经验（top-5）

图书管理员支持跨Agent检索：
```python
# Agent内部检索自己的知识
results = self.vectordb.query("功效护肤市场趋势", n_results=5)

# 通过图书管理员检索其他Agent的知识
results = librarian.get_agent_knowledge("researcher", "功效护肤数据")

# 检索共享素材库
results = librarian.search_shared("护肤行业报告")
```

### 反思（Reflection）

#### 自动反思
每次任务完成后触发：
1. LLM分析本次执行的输入输出
2. 提取经验教训（做得好的 + 需改进的）
3. 保存为反思记录
4. **规则晋升**：同一教训出现3次以上，自动晋升为正式规则（confidence递增）

#### 人工反思
用户修改文章后触发：
1. 系统对比原稿和用户修改版的diff
2. LLM分析修改模式，提取隐含偏好
3. 生成规则，`source="human"`，初始置信度更高（0.7 vs 自动的0.5）

```bash
# 提交人工修改，触发反思
writing-agent edit abc123 ./my_edited_article.md
```

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| LLM | DeepSeek API | deepseek-chat (V3) + deepseek-reasoner (R1) |
| 网页爬取 | [Crawl4AI](https://github.com/unclecode/crawl4ai) | 异步爬取、反爬绕过、Markdown提取 |
| 文章生成 | [cibe-whitepaper](https://github.com/hamburger-lie/cibe-whitepaper) | 结构化文章模板（提示词已重写） |
| 向量存储 | ChromaDB | 每Agent独立的语义检索 |
| 结构化存储 | SQLite (WAL模式) | 规则、历史、反思记录 |
| 搜索引擎 | Bing/Google/Serper API | 自主联网搜索 |
| CLI框架 | Typer + Rich | 命令行交互界面 |
| 包管理 | uv | Python依赖管理 |

## 快速开始

### 前置条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 包管理工具
- DeepSeek API Key
- 搜索引擎 API Key（Bing/Serper，用于联网搜索）

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd 写作agent

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 配置

编辑 `.env` 文件：

```env
# DeepSeek
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 搜索引擎 (选一个)
SEARCH_ENGINE=serper
SEARCH_API_KEY=your_search_key

# cibe-whitepaper (可选)
WHITEPAPER_API_URL=http://localhost:8000
```

### 使用

```bash
# 初始化数据目录和数据库
writing-agent init

# 完整写作流水线
writing-agent write "2026年中国功效护肤市场趋势分析"

# 单独调研
writing-agent research "AI在美业的应用场景" --max-urls 15

# 审核已有草稿
writing-agent review ./draft.md

# 提交人工修改（触发反思）
writing-agent edit <task_id> ./edited_article.md

# 润色已有文章
writing-agent polish ./article.md

# 查看历史
writing-agent history --agent writer --limit 10

# 知识库管理
writing-agent knowledge search "护肤成分功效" --shared
writing-agent knowledge rules --agent reviewer
writing-agent knowledge add ./reference.md --agent writer
```

## CLI 命令速览

| 命令 | 说明 |
|------|------|
| `writing-agent init` | 初始化数据目录和数据库 |
| `writing-agent write <topic>` | 完整流水线：策划→调研→写作→润色→审核→发布 |
| `writing-agent research <topic>` | 单独执行调研，输出结构化素材 |
| `writing-agent review <file>` | 对已有草稿执行审核 |
| `writing-agent polish <file>` | 对已有文章执行润色 |
| `writing-agent edit <task_id> <file>` | 提交人工修改，触发反思提取规则 |
| `writing-agent history` | 查看任务历史 |
| `writing-agent knowledge search <query>` | 语义搜索知识库 |
| `writing-agent knowledge rules` | 查看/管理写作规则 |
| `writing-agent knowledge add <file>` | 手动添加知识到知识库 |
| `writing-agent config show` | 显示当前配置 |

## 项目结构

```
src/writing_agent/
├── main.py                  # CLI入口点
├── config.py                # 配置管理（pydantic-settings）
├── controller/              # 流水线控制
│   ├── pipeline.py          # 主编排器：串联6个Agent
│   ├── task.py              # PipelineTask数据模型（流水线状态）
│   └── publisher.py         # 文章发布（cibe-whitepaper集成）
├── agents/                  # 6个子Agent实现
│   ├── base.py              # BaseAgent抽象基类（生命周期、存储、反思）
│   ├── planner.py           # 策划Agent
│   ├── researcher.py        # 调研Agent
│   ├── writer.py            # 主笔Agent
│   ├── polisher.py          # 润色Agent
│   ├── reviewer.py          # 审核Agent
│   └── librarian.py         # 图书管理员Agent
├── llm/                     # LLM调用层
│   ├── provider.py          # DeepSeek API封装（重试、JSON解析、模型切换）
│   ├── models.py            # 模型常量、角色→模型映射
│   └── prompts/             # 各角色的提示词模板
├── storage/                 # 存储层
│   ├── sqlite_store.py      # SQLite操作（规则CRUD、历史记录）
│   ├── vector_store.py      # ChromaDB操作（添加、查询、删除）
│   ├── schema.py            # SQLite表结构定义
│   └── manager.py           # StorageManager：为每个Agent分配独立存储
├── tools/                   # 外部工具封装
│   ├── web_search.py        # 搜索引擎API（Bing/Serper）
│   ├── web_scraper.py       # Crawl4AI封装
│   └── whitepaper.py        # cibe-whitepaper集成
├── reflection/              # 反思系统
│   ├── auto_reflect.py      # 自动反思（任务后触发）
│   └── human_reflect.py     # 人工编辑反思（diff分析）
└── cli/                     # CLI界面
    ├── app.py               # Typer应用根
    └── commands/            # 各命令实现
```

## 模型选择策略

- **deepseek-reasoner (R1)**：用于需要深度推理的环节（策划、审核），R1的思维链能力适合结构化分析
- **deepseek-chat (V3)**：用于需要快速迭代的环节（调研、写作、润色、图书管理），V3更快且支持温度调节

注意：R1 不支持 `temperature`、`top_p` 等参数，LLM调用层会自动处理这个差异。

## 错误处理与降级策略

| 故障场景 | 降级行为 |
|----------|----------|
| 搜索引擎API不可用 | 跳过联网调研，仅用已有知识库 |
| Crawl4AI爬取失败 | 跳过该URL，继续爬取其他URL（至少需2个成功） |
| R1模型不可用 | 降级到V3模型（质量降低但可用） |
| ChromaDB损坏 | 降级为无语义检索模式，仅用SQLite规则 |
| 审核多轮不通过 | 标记为"草稿"发布，保留审核问题供人工处理 |
| 流水线中断 | 各阶段输出实时保存，支持 `--resume` 从断点恢复 |

## 开发路线

- [x] 阶段1：项目骨架 + README
- [ ] 阶段2：基础设施（config、storage、llm provider、base agent）
- [ ] 阶段3：核心流水线（planner → writer，最小可用版本）
- [ ] 阶段4：调研工具（web search + Crawl4AI + researcher agent）
- [ ] 阶段5：润色 + 审核循环
- [ ] 阶段6：图书管理员 + 跨Agent知识管理
- [ ] 阶段7：反思系统（自动 + 人工）
- [ ] 阶段8：CLI完善 + 错误处理加固
- [ ] 阶段9：Web界面（后续）

## License

MIT
