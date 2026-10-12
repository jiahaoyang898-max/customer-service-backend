# CLAUDE.md

本文档为 Claude Code（claude.ai/code）在该代码库中工作时提供指导。

## 项目概述

这是一个 **AI 驱动的电商客服后端**（电商小二）。系统通过基于任务的对接话系统，使用大语言模型（LLM）处理客户关于订单、物流、商品和退款的咨询。

## 技术栈

- **Web 框架**：FastAPI + Uvicorn
- **数据库**：MySQL + SQLAlchemy 异步驱动（`aiomysql`）
- **LLM 集成**：LangChain + OpenAI 兼容 API（当前使用 SiliconFlow 的 DeepSeek-V4-Flash）
- **配置管理**：Pydantic Settings，通过 `.env` 文件配置
- **任务流**：YAML 定义对话流程，配合 Jinja2 模板

## 前置条件

**必须先启动外部电商服务**（提供订单/商品 API）：
```powershell
cd external/ecommerce-service-backend
uvicorn app.main:app --reload --port 18081
```

后端连接 `http://127.0.0.1:18081` 获取订单和商品数据。

## 运行应用

```powershell
# 直接运行 Python
python main.py

# 或使用 uvicorn
uvicorn api.app:app --host 127.0.0.1 --port 18082
```

**注意**：需要 MySQL 服务运行，地址在 `.env` 中配置（默认：`127.0.0.1:3306`）。

## 依赖管理

项目使用 `pyproject.toml`。安装/同步依赖：
```bash
uv sync  # 使用 uv
# 或
pip install -e .
```

## API 端点

- `POST /api/chat` - 主聊天接口，接受文本或对象（订单/商品）消息
- `GET /api/chat/history` - 根据 sender_id 获取对话历史

## 架构设计

代码库遵循 **领域驱动设计（DDD）**，各层职责清晰分离：

### 各层职责

| 层级 | 职责 |
|------|------|
| `api/` | FastAPI 路由、请求/响应模型、依赖注入 |
| `service/` | 对话处理编排、状态加载与保存 |
| `engine/` | 核心对话处理（DialogueEngine） |
| `domain/` | 领域模型（消息、状态）- 纯业务概念 |
| `task/` | 任务流执行、命令处理、动作执行 |
| `plan/` | 轮次规划（基于 LLM 的意图识别）与验证 |
| `knowledge/` | FAQ 和 RAG 知识检索 |
| `clarify/` | 用户意图不明确时的澄清响应 |
| `chitchat/` | 闲聊处理 |
| `repository/` | 对话状态持久化 |
| `infrastructure/` | 数据库、HTTP 客户端、LLM 客户端初始化 |
| `prompts/` | Jinja2 提示词模板和历史消息构建 |

### 对话流程

1. **API 层** 接收聊天请求 → 转换为领域 `UserMessage`
2. **DialogueService** 从数据库加载 `DialogueState`
3. **DialogueEngine** 处理消息：
   - **TurnPlanner**（LLM）预测用户意图 → 返回 `TurnPlan`（任务、知识或闲聊）
   - **TurnPlanValidator** 验证计划
   - 分发到对应处理器：
     - **TaskHandler**：执行 YAML 定义的流程（订单查询、物流、退款等）
     - **KnowledgeHandler**：RAG/FAQ 检索
     - **ChitChatHandler**：闲聊
     - **ClarifyResponder**：意图不清时请求澄清
4. `DialogueState` 持久化回 MySQL
5. 返回响应给客户端

### 任务流（YAML）

业务流定义在 `flow_config/` 目录下：
- `user_flows.yml` - 面向客户的流程（订单状态、物流、退款、商品推荐、人工转接）
- `system_flows.yml` - 系统流程（入门引导）

流程包含步骤：`start`、`collect`（槽位收集）、`action`、`end`。动作通过 `task/action/custom/` 模块执行。

## 关键文件

- `api/app.py` - FastAPI 应用，包含生命周期管理
- `api/routers/chat_router.py` - 聊天接口
- `engine/dialogue_engine.py` - 核心对话编排
- `plan/turn_planner.py` - LLM 意图分类
- `domain/state.py` - DialogueState 聚合根，管理会话和轮次
- `flow_config/user_flows.yml` - 业务流定义
- `conf/config.py` - 环境变量配置