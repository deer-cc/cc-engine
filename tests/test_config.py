"""
config.json 合法性测试 — 只断言"合法 JSON + 必需 key 存在"，
不写死具体值（避免换 LLM 提供商/端口时测试误报）。
"""
import json
import warnings
from pathlib import Path

import pytest

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

# 必需 key：缺失任一个服务都跑不起来
REQUIRED_KEYS = [
    "llm_base_url", "llm_api_key", "llm_model",
    "max_turns", "history_window", "kb_top_k",
]


def test_config_is_valid_json():
    """config.json 必须是合法 JSON（不能带注释/首行杂项）"""
    content = CONFIG_FILE.read_text(encoding="utf-8")
    data = json.loads(content)  # 解析失败直接抛错
    assert isinstance(data, dict), "config.json 顶层必须是对象"


def test_required_keys_present():
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in data]
    assert not missing, f"config.json 缺必需 key: {missing}"


def test_corrupt_config_falls_back_with_warning():
    """损坏的 config.json → load_config 应 fallback 到默认值并打 warning（不静默吞）"""
    import sys
    import types

    # 隔离加载：构造一个指向不存在文件的 main 模块副本，避免污染全局缓存
    import importlib
    spec = importlib.util.spec_from_file_location(
        "main_corrupt_test", Path(__file__).parent.parent / "src" / "main.py")
    main_mod = importlib.util.module_from_spec(spec)
    sys.modules["main_corrupt_test"] = main_mod
    spec.loader.exec_module(main_mod)

    # 把 CONFIG_FILE 指向一个损坏文件
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    tmp.write("这不是合法 JSON {{{")
    tmp.close()

    main_mod.CONFIG_FILE = Path(tmp.name)
    main_mod._config_cache = None

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            cfg = main_mod.load_config()

        # fallback 到默认值：必需 key 都在
        for k in REQUIRED_KEYS:
            assert k in cfg, f"fallback 后缺 key {k}"
        # 且必须打过 warning（不能静默）
        assert any("config" in str(w.message).lower() for w in caught), \
            "损坏 config 未触发 warning，违反'不静默吞'原则"
    finally:
        os.unlink(tmp.name)
        main_mod.CONFIG_FILE = CONFIG_FILE
        main_mod._config_cache = None
