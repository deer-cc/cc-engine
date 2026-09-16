"""
客服引擎 v1.0 — CLI 入口
用法：
  python main.py              启动服务
  python main.py test         运行测试
"""
import sys
import asyncio
from pathlib import Path

# 确保当前目录在 path 中
sys.path.insert(0, str(Path(__file__).parent))


def cmd_start():
    """启动 FastAPI 服务"""
    import uvicorn
    from src.main import app
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
