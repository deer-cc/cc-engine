"""
客服引擎 v1.0 — CLI 入口
用法：
  python main.py              启动服务
  python main.py test         运行测试

注意(2026-10-26): Windows/PowerShell 下用 `python -m src.main` 入口会导致
uvicorn 静默崩溃。启动服务请用 uvicorn CLI 形式:
  python -m uvicorn src.main:app --host 127.0.0.1 --port 8899
cmd_start 已改为调 uvicorn.run 直接接管(等价形式), 但最稳的仍是上面的命令行。
"""
import sys
import asyncio
from pathlib import Path

# 确保当前目录在 path 中
sys.path.insert(0, str(Path(__file__).parent))


def cmd_start():
    """启动 FastAPI 服务（uvicorn CLI 形式，Windows 下最稳）"""
    import uvicorn
    print("🚀 客服引擎启动中...")
    print("📍 演示页面: http://127.0.0.1:8899")
    print("📊 API 文档: http://127.0.0.1:8899/docs")
    uvicorn.run("src.main:app", host="127.0.0.1", port=8899, reload=False)


def cmd_test():
    """运行测试"""
    import pytest
    sys.exit(pytest.main([str(Path(__file__).parent / "tests"), "-v"]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        cmd_test()
    else:
        cmd_start()
