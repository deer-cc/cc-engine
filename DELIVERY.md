# 客服引擎 v2.0 — 交付指南

> 最后更新：2026-10-14

---

## 一、项目结构

```
客服引擎/
├── src/                    # 核心源码
│   ├── main.py             # FastAPI 入口（P0: await修复+config缓存+对话懒加载）
│   ├── intent.py           # 意图识别（LLM+关键词双路，P1: 超时8s+关键词精简）
│   ├── dialog.py           # 多轮对话（P2: LLM回复生成，P3: 完整异步化）
│   ├── rag.py              # RAG检索（TTL缓存+关键词统一）
│   ├── confidence.py       # 置信度校准
│   └── query_rewriter.py   # 查询改写
├── knowledge/              # 知识库（FAQ+物流+退换规则）
├── static/                 # 前端演示页面
├── tests/                  # 66个单元测试，100%通过
├── Dockerfile              # Docker一键部署
├── docker-compose.yml      # 本地开发环境
├── config.json             # 运行配置（需修改LLM地址）
├── requirements.txt        # Python依赖
└── README.md               # 项目文档
```

---

## 二、快速启动

### 方式A：直接运行（推荐演示用）

```bash
# 1. 进入项目目录
cd 客服引擎

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 修改配置（关键！）
# 编辑 config.json，填入可用的 LLM API 地址
# 或复制 .env.example 为 .env 并填入密钥

# 5. 启动服务
python -m uvicorn src.main:app --host 127.0.0.1 --port 8899

# 6. 浏览器打开
http://127.0.0.1:8899
```

### 方式B：Docker 部署

```bash
# 1. 修改 docker-compose.yml 中的 LLM 地址
# 2. 启动
docker-compose up -d

# 3. 访问
http://localhost:8899

# 4. 查看日志
docker-compose logs -f
```

---

## 三、LLM API 配置

**重要：** 本项目需要连接 LLM 服务，请根据你的环境选择：

### 选项1：使用 cc-connect 代理（本地已有）
```json
// config.json
{
  "llm_base_url": "http://127.0.0.1:15721",
  "llm_api_key": "PROXY_MANAGED",
  "llm_model": "claude-opus-4-8-20251101"
}
```

### 选项2：使用 DeepSeek API（推荐外部交付）
```json
{
  "llm_base_url": "https://api.deepseek.com/v1",
  "llm_api_key": "你的DeepSeek_API_Key",
  "llm_model": "deepseek-chat"
}
```

### 选项3：使用 OpenAI API
```json
{
  "llm_base_url": "https://api.openai.com/v1",
  "llm_api_key": "你的OpenAI_API_Key",
  "llm_model": "gpt-4o-mini"
}
```

---

## 四、API 接口

| 接口 | 方法 | 说明 |
|:-----|:----:|:-----|
| `/` | GET | 前端演示页面 |
| `/chat` | POST | 对话入口 |
| `/intent` | POST | 意图识别 |
| `/kb/search` | POST | 知识库检索 |
| `/kb/list` | GET | 列出知识库文件 |
| `/health` | GET | 健康检查 |
| `/conversations` | GET | 列出所有对话 |
| `/stats` | GET | 系统统计 |

### /chat 请求示例
```json
POST /chat
{
  "message": "什么时候发货？",
  "session_id": "user_001"
}
```

响应：
```json
{
  "reply": "关于物流问题：...",
  "intent": "shipping",
  "confidence": 0.92,
  "confidence_level": "high",
  "session_id": "user_001",
  "turn_count": 1
}
```

---

## 五、测试验证

```bash
# 运行全部测试
pytest tests/ -v

# 预期结果：66 passed
```

---

## 六、注意事项

1. **conversations/ 目录**：对话历史自动保存在此，交付前可清空
2. **.env 文件**：包含 API Key，不要提交到公开仓库
3. **LLM 依赖**：演示时需要能访问 LLM API，否则走关键词兜底
4. **知识库扩展**：在 knowledge/ 下添加 .md 文件即可自动加载

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|:----:|:----:|:-----|
| v1.0 | 2026-09-08 | 初始版本 |
| v1.1 | 2026-09-19 | 查询改写+置信度校准+低置信度澄清 |
| v2.0 | 2026-10-14 | P0-P3全量修复：await缺失、缓存优化、异步化、LLM回复生成、打字机效果 |

---

*本项目为AI应用工程师作品集，展示完整工程能力。*
