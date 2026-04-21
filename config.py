import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API 密钥
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# QQ Bot 配置
QQ_BOT_ENABLED = os.getenv("QQ_BOT_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")
QQ_BOT_API_URL = os.getenv("QQ_BOT_API_URL", "")
QQ_BOT_SECRET = os.getenv("QQ_BOT_SECRET", "")
QQ_BOT_PORT = int(os.getenv("QQ_BOT_PORT", "8080"))

# 调试检查
if not TELEGRAM_TOKEN and not QQ_BOT_ENABLED:
    raise ValueError("错误：未检测到 TELEGRAM_TOKEN，且 QQ Bot 未启用。请检查 .env 配置。")
if not GROQ_API_KEY and not GEMINI_API_KEY:
    raise ValueError("错误：至少需要一个 API Key（GROQ_API_KEY 或 GEMINI_API_KEY）！ 请检查 .env 配置")
if QQ_BOT_ENABLED and not QQ_BOT_API_URL:
    raise ValueError("错误：已启用 QQ Bot，但未配置 QQ_BOT_API_URL。请检查 .env 配置。")

if TELEGRAM_TOKEN:
    print(f"Telegram Token 已加载，长度为: {len(TELEGRAM_TOKEN)}")
if QQ_BOT_ENABLED:
    print(f"QQ Bot 已启用，OneBot API URL: {QQ_BOT_API_URL}, 监听端口: {QQ_BOT_PORT}")

# 模型配置（按 API 分组）
MODEL_LIST = {
    # Groq 模型
    "groq_fast": {"api": "groq", "model": "llama-3.3-70b-versatile"},
    "groq_smart": {"api": "groq", "model": "mixtral-8x7b-32768"},
    # Gemini 模型
    "gemini_fast": {"api": "gemini", "model": "gemini-2.5-flash"},
    "gemini_smart": {"api": "gemini", "model": "gemini-1.5-pro"},
    # Grok 模型
    "grok_fast":  {"api": "grok", "model": "grok-4-1-fast"},  
    "grok_smart": {"api": "grok", "model": "grok-4.20"},        
}

# 默认模型列表映射（兼容旧格式）
DEFAULT_MODELS = {
    "fast": "groq_fast",
    "smart": "groq_smart"
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