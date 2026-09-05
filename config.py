import os
import json
import re
import urllib.request
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API 密钥
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROK_API_KEY = os.getenv("GROK_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()

# QQ Bot 配置
QQ_BOT_ENABLED = os.getenv("QQ_BOT_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")
QQ_BOT_API_URL = os.getenv("QQ_BOT_API_URL", "")
QQ_BOT_SECRET = os.getenv("QQ_BOT_SECRET", "")
QQ_BOT_PORT = int(os.getenv("QQ_BOT_PORT", "8080"))

# 调试检查
if not TELEGRAM_TOKEN and not QQ_BOT_ENABLED:
    raise ValueError("错误：未检测到 TELEGRAM_TOKEN，且 QQ Bot 未启用。请检查 .env 配置。")
if QQ_BOT_ENABLED and not QQ_BOT_API_URL:
    raise ValueError("错误：已启用 QQ Bot，但未配置 QQ_BOT_API_URL。请检查 .env 配置。")

if TELEGRAM_TOKEN:
    print(f"Telegram Token 已加载，长度为: {len(TELEGRAM_TOKEN)}")
if QQ_BOT_ENABLED:
    print(f"QQ Bot 已启用，OneBot API URL: {QQ_BOT_API_URL}, 监听端口: {QQ_BOT_PORT}")

# 模型配置（按 API 分组）
MODEL_LIST = {
    # Groq 模型
    "groq_fast": {"api": "groq", "model": "qwen/qwen3.6-27b"},
    "groq_smart": {"api": "groq", "model": "qwen/qwen3.8-27b"},
    "groq_gpt_oss_120b": {"api": "groq", "model": "openai/gpt-oss-120b"},
    "groq_gpt_oss_20b": {"api": "groq", "model": "openai/gpt-oss-20b"},
    "groq_compound": {"api": "groq", "model": "groq/compound"},
    "groq_compound_mini": {"api": "groq", "model": "groq/compound-mini"},
    "groq_allam": {"api": "groq", "model": "allam-2-7b"},
    # Gemini 模型
    "gemini_fast": {"api": "gemini", "model": "gemini-2.5-flash"},
    "gemini_smart": {"api": "gemini", "model": "gemini-3.1-flash-lite"},
    "gemini_2_5_pro": {"api": "gemini", "model": "gemini-2.5-pro"},
    "gemini_2_5_flash_lite": {"api": "gemini", "model": "gemini-2.5-flash-lite"},
    "gemini_flash_latest": {"api": "gemini", "model": "gemini-flash-latest"},
    "gemini_flash_lite_latest": {"api": "gemini", "model": "gemini-flash-lite-latest"},
    "gemini_pro_latest": {"api": "gemini", "model": "gemini-pro-latest"},
    "gemini_3_flash_preview": {"api": "gemini", "model": "gemini-3-flash-preview"},
    "gemini_3_1_pro_preview": {"api": "gemini", "model": "gemini-3.1-pro-preview"},
    "gemini_3_1_flash_lite_preview": {"api": "gemini", "model": "gemini-3.1-flash-lite-preview"},
    "gemini_3_5_flash": {"api": "gemini", "model": "gemini-3.5-flash"},
    "gemini_3_5_flash_lite": {"api": "gemini", "model": "gemini-3.5-flash-lite"},
    "gemini_3_6_flash": {"api": "gemini", "model": "gemini-3.6-flash"},
    "gemini_3_7_flash": {"api": "gemini", "model": "gemini-3.7-flash"},
    "gemini_3_8_flash": {"api": "gemini", "model": "gemini-3.8-flash"},
    "gemini_omni_flash_preview": {"api": "gemini", "model": "gemini-omni-flash-preview"},
    "gemini_omni_1_1_flash": {"api": "gemini", "model": "gemini-omni-1.1-flash"},
    "gemma_4_26b": {"api": "gemini", "model": "gemma-4-26b-a4b-it"},
    "gemma_4_31b": {"api": "gemini", "model": "gemma-4-31b-it"},
    # Grok 模型
    "grok_fast":  {"api": "grok", "model": "grok-4-1-fast"},  
    "grok_smart": {"api": "grok", "model": "grok-4.20"},        
}


def refresh_ollama_models():
    """从本机 Ollama 刷新已安装模型，不可用时保留其他供应商。"""
    for key in [key for key, value in MODEL_LIST.items() if value.get("api") == "ollama"]:
        del MODEL_LIST[key]

    tags_url = f"{OLLAMA_BASE_URL.rsplit('/v1', 1)[0]}/api/tags"
    try:
        with urllib.request.urlopen(tags_url, timeout=2) as response:
            models = json.load(response).get("models", [])
    except (OSError, ValueError):
        models = []

    model_names = set()
    for item in models:
        model_name = item.get("name") or item.get("model")
        if not model_name:
            continue
        model_names.add(model_name)
        model_key = "ollama_" + re.sub(r"[^a-zA-Z0-9]+", "_", model_name).strip("_").lower()
        MODEL_LIST[model_key] = {"api": "ollama", "model": model_name}

    # 允许显式配置远程或暂时无法枚举的 Ollama 模型。
    if OLLAMA_MODEL and OLLAMA_MODEL not in model_names:
        model_key = "ollama_" + re.sub(r"[^a-zA-Z0-9]+", "_", OLLAMA_MODEL).strip("_").lower()
        MODEL_LIST[model_key] = {"api": "ollama", "model": OLLAMA_MODEL}

    return models


OLLAMA_MODELS = refresh_ollama_models()

# 云端模型与本地 Ollama 至少配置一种；Ollama 可单独运行。
if not any((GROQ_API_KEY, GEMINI_API_KEY, GROK_API_KEY, OLLAMA_MODELS, OLLAMA_MODEL)):
    raise ValueError("错误：请至少配置一个云端 API Key、正在运行的 Ollama，或 OLLAMA_MODEL。")

# 默认模型列表映射（兼容旧格式）。没有云端 Key 时默认使用本地模型。
DEFAULT_MODELS = {
    "fast": "groq_fast",
    "smart": "groq_smart"
}
if not any((GROQ_API_KEY, GEMINI_API_KEY, GROK_API_KEY)):
    _default_ollama_key = next(
        key for key, value in MODEL_LIST.items() if value.get("api") == "ollama"
    )
    DEFAULT_MODELS = {
        "fast": _default_ollama_key,
        "smart": _default_ollama_key,
    }

# 用户配置存储（现由数据库管理，保留字典用于向后兼容）
user_keys = {}  # 格式: {user_id: {"groq": "gsk_xxxx", "gemini": "xxx_xxxx"}}
user_api_provider = {}  # 格式: {user_id: "groq"} 或 {user_id: "gemini"}

# 初始化数据库
try:
    from core.database import init_db, get_user_api_keys, get_user_api_provider
    init_db()
except ImportError:
    print("警告：数据库模块加载失败，将使用内存存储（关机会丢失数据）")

# 数据库配置
DB_PATH = os.getenv("DB_PATH", "march7_bot.db")   # 默认存到项目根目录
