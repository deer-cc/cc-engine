# cc-engine Windows 部署手册（实测版）

> 本文档基于 2026-10-30 本机实际部署过程编写，所有命令均在 Windows 10 + Python 3.11 环境验证通过。
> 适用对象：拿到源码后需要在本机/客户现场把服务跑起来的人。

---

## 一、环境要求

| 项 | 要求 | 本机实测 |
|----|------|---------|
| 操作系统 | Windows 10/11、Linux、macOS | Windows 10 Pro for Workstations 19045 |
| Python | 3.10+ | 3.11.9 |
| 内存 | ≥ 2 GB | — |
| 磁盘 | ≥ 500 MB（含虚拟环境与依赖） | — |
| 网络 | 能访问 PyPI（国内建议用镜像） | 走清华源 |

不依赖 GPU、不依赖 Docker、不依赖外网大模型也可以启动（见第五节降级模式）。

---

## 二、快速部署（5 步）

```powershell
# 1. 进入项目目录
cd D:\AI软件\桌面交付\cc-engine-main

# 2. 创建虚拟环境（隔离依赖，不污染系统 Python）
py -3.11 -m venv .venv

# 3. 升级 pip 并安装依赖（国内用清华镜像，速度从 10+ 分钟降到 1 分钟）
.\.venv\Scripts\python.exe -m pip install -q --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 运行测试，确认环境正确
.\.venv\Scripts\python.exe -m pytest -q
# 预期输出：68 passed

# 5. 启动服务
.\.venv\Scripts\python.exe .\__main__.py
```

启动成功输出：

```
🚀 客服引擎启动中...
📍 演示页面: http://127.0.0.1:8899
📊 API 文档: http://127.0.0.1:8899/docs
INFO:     Uvicorn running on http://127.0.0.1:8899
```

---

## 三、验证清单

按顺序验证，每步都有明确预期，任何一步不符即停止排查。

| # | 验证项 | 命令 | 预期 |
|---|--------|------|------|
| 1 | 单元测试 | `pytest -q` | `68 passed` |
| 2 | 健康检查 | `curl http://127.0.0.1:8899/health` | HTTP 200 |
| 3 | 演示页面 | 浏览器打开 `http://127.0.0.1:8899/` | 出现对话框页面 |
| 4 | API 文档 | 浏览器打开 `http://127.0.0.1:8899/docs` | Swagger 页面 |
| 5 | 意图识别 | 见下方对话测试 | 返回 intent + confidence |
| 6 | 知识库 | `curl http://127.0.0.1:8899/kb/list` | 返回知识库文档列表 |

对话测试（PowerShell，**必须用 UTF-8 字节发送，否则中文会乱码**）：

```powershell
$json = '{"message":"这个能退货吗","session_id":"test1"}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
Invoke-WebRequest -Uri "http://127.0.0.1:8899/chat" -Method Post -Body $bytes `
  -ContentType "application/json; charset=utf-8" -UseBasicParsing
```

预期：`intent=returns`、`confidence≈0.97`、`confidence_level=high`、`reply` 为中文退货话术。

---

## 四、端口与配置

配置文件 `config.json`：

```json
{
  "llm_base_url": "http://127.0.0.1:15721",
  "llm_api_key": "PROXY_MANAGED",
  "llm_model": "claude-opus-4-8-20251101",
  "max_turns": 10,
  "history_window": 6,
  "kb_top_k": 3,
  "port": 8899,
  "host": "127.0.0.1"
}
```

| 字段 | 说明 | 改法 |
|------|------|------|
| `port` | 服务端口，默认 8899 | 端口冲突时改成 8900 等 |
| `host` | 监听地址 | `127.0.0.1` 仅本机；改 `0.0.0.0` 可让同局域网设备访问 |
| `llm_base_url` / `llm_api_key` / `llm_model` | 大模型接口 | 换成可用的 Anthropic 兼容接口；不配也能跑（降级模式） |

---

## 五、无大模型降级模式（重要）

`llm_base_url` 指向的接口不可用时，服务**不会崩溃**，会自动降级为「知识库检索 + 模板化回复」：

- 意图识别、知识检索、置信度判定全部正常
- 回复内容由知识库拼装，不再经大模型润色
- 适合演示、断网环境、以及验证链路本身是否正常

实测：接口返回 404 时，`/chat` 仍返回 200，`intent=returns`、`confidence=0.97`，回复是完整可读的中文话术。

**这一点在客户现场很关键**：模型接口挂了不等于系统挂了，用户可以继续用基础功能，运维有时间定位问题。

---

## 六、常见故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| `pip install` 极慢或超时 | 默认走 PyPI 官方源，国内网络慢 | 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `jieba` 安装卡在 Building wheel | 源码编译，首次较慢 | 等 1–2 分钟，正常现象 |
| 启动报 `Address already in use` / 端口占用 | 8899 被上一个进程占用 | `netstat -ano \| findstr :8899` 找到 PID，`taskkill /PID <pid> /F`；或改 `config.json` 的 `port` |
| 浏览器打开 `/` 是 404 | 旧版本（交付包 v2.0）未挂载静态目录 | 使用 GitHub main 分支版本（已修复），或直接访问 `/docs` |
| 对话返回乱码 | 请求体未按 UTF-8 编码（PowerShell 默认非 UTF-8） | 用 `[System.Text.Encoding]::UTF8.GetBytes()` 转字节再发送 |
| 测试数不是 68 | 使用的是旧交付包 v2.0（52 个测试） | 用 GitHub main 分支版本 |
| 关闭终端后服务停止 | 前台进程随终端退出 | 用后台方式启动，见第七节 |

---

## 七、后台运行与停止

**后台启动（关闭终端不中断）：**

```powershell
$dst = "D:\AI软件\桌面交付\cc-engine-main"
Start-Process -FilePath "$dst\.venv\Scripts\python.exe" -ArgumentList "`"$dst\__main__.py`"" `
  -WorkingDirectory $dst -WindowStyle Hidden `
  -RedirectStandardOutput "$dst\run.log" -RedirectStandardError "$dst\run.err.log"
```

**查看日志：**

```powershell
Get-Content "$dst\run.err.log" -Tail 20
```

**停止服务：**

```powershell
Get-Process python | Where-Object { $_.Path -like "*cc-engine-main*" } | Stop-Process -Force
```

**开机自启（可选）**：用「任务计划程序」添加一个登录时触发的任务，操作填上面的 `python.exe`，参数填 `__main__.py`，起始位置填项目目录。

---

## 八、本次部署实际记录

| 时间 | 操作 | 结果 |
|------|------|------|
| 2026-10-30 | 解压 GitHub main 分支 | 完整仓库（src/docs/tests/static/.github） |
| | `py -3.11 -m venv .venv` | 成功 |
| | pip 装依赖（清华源） | 30 个包，约 1 分钟 |
| | `pytest -q` | **68 passed in 19.09s** |
| | 启动服务 | `uvicorn 127.0.0.1:8899` 正常 |
| | `/` `/health` `/docs` `/kb/list` | 全部 200 |
| | 三条真实提问测试 | returns(0.97) / shipping(0.97) / returns(0.95) 全命中 |

未配置大模型接口，全部结果来自降级模式，说明检索与意图链路独立可用。

---

## 九、后续可做（非必须）

1. **局域网演示**：`host` 改 `0.0.0.0`，同一 WiFi 下手机/其他电脑可用 `http://<本机IP>:8899` 访问
2. **公网演示**：Cloudflare Tunnel（免费、无需服务器、无需备案），把本机 8899 映射成临时公网地址
3. **Docker 部署**：仓库已带 `Dockerfile` / `docker-compose.yml`，装 Docker Desktop 后 `docker compose up` 即可
4. **进程守护**：任务计划程序 / NSSM 注册为 Windows 服务，实现崩溃自启
