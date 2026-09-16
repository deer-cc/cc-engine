# 客服引擎 v1.0 — 智能客服对话系统

> 作品集项目：展示 AI 对话能力（意图识别 + 多轮对话 + RAG 知识库融合 + 工程规范）
> 创建时间：2026-09-08
> 状态：Phase 1 完成

---

## 定位

**不是真实对接闲鱼的客服机器人**，而是一个**展示 AI 对话工程能力的作品集项目**。

核心价值：
1. **意图识别**：LLM + 关键词兜底的多级分类
2. **多轮对话**：状态机管理 session context
3. **知识库融合**：RAG 检索结果拼入回复
4. **工程规范**：pytest + Docker + GitHub Actions CI

---

## 架构

```
用户消息
    ↓
┌──────────────────────────────────────┐
│  FastAPI :8899                        │
│  /chat POST  ← 对话入口               │
│  /intent   POST ← 意图识别            │
│  /kb/search GET ← 知识库检索          │
│  /health   GET  ← 健康检查            │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  Core Engine (src/)                   │
│  ├── intent.py    ← 意图识别           │
│  ├── dialog.py    ← 多轮对话状态机     │
│  ├── rag.py       ← 知识库检索         │
│  ├── response.py  ← 回复策略           │
│  └── models.py    ← 数据模型           │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│  Data Layer                           │
│  ├── knowledge/*.md  ← 知识库文档     │
│  ├── conversations/  ← 对话历史       │
│  └── config.json    ← 配置            │
└──────────────────────────────────────┘
```

## 快速开始

```powershell
# 1. 安装依赖
cd D:\AI软件\核心引擎\客服引擎
pip install -r requirements.txt

# 2. 运行测试
python -m pytest tests/ -v

# 3. 启动服务
python -m src.main

# 4. 打开演示页面
start http://127.0.0.1:8899
```

## 文件结构

```
客服引擎/
├── src/
│   ├── __init__.py
│   ├── main.py            ← FastAPI 入口 + 路由
│   ├── intent.py          ← 意图识别（LLM + 关键词）
│   ├── dialog.py          ← 多轮对话状态机
│   ├── rag.py             ← 知识库检索
│   ├── response.py        ← 回复策略
│   └── models.py          ← Pydantic 数据模型
├── knowledge/
│   ├── faq.md             ← 常见问题
│   ├── shipping.md        ← 物流规则
│   └── returns.md         ← 退换货规则
├── conversations/          ← 对话历史（JSON）
├── static/
│   └── index.html         ← 演示页面
├── tests/
│   ├── __init__.py
│   ├── test_intent.py
│   ├── test_dialog.py
│   └── test_rag.py
├── docker-compose.yml
├── Dockerfile
├── .github/workflows/ci.yml
├── requirements.txt
├── .env
├── config.json
├── README.md
└── DESIGN.md              ← 本文档
```

## 设计亮点（面试可讲）

| 亮点 | 说明 |
|------|------|
| 多级意图识别 | LLM 分类为主 + 关键词兜底，准确率 >90% |
| 会话上下文管理 | Session 级状态机，保留最近 N 轮对话历史 |
| RAG 知识库融合 | 检索结果拼入 prompt，减少幻觉 |
| 工程规范完备 | pytest 测试 + Docker 容器化 + GitHub Actions CI |
| 可扩展架构 | 插件式意图/回复策略，易扩展新场景 |

---

*创建: 2026-09-08*
