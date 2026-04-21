from openai import OpenAI
from google import genai
from core.state import user_model, get_state
from core.memory import get_memory
from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROK_API_KEY,
    MODEL_LIST,
    DEFAULT_MODELS,
    user_keys
)
from prompt.march7 import get_prompt

# 数据库支持（可选）
try:
    from core.database import get_user_api_keys
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


# =========================
# 🔑 获取用户 API Key
# =========================
def get_api_key(user_id, provider):
    if DB_AVAILABLE:
        keys = get_user_api_keys(user_id) or {}
    else:
        keys = user_keys.get(user_id, {}) if isinstance(user_keys.get(user_id), dict) else {}

    # 优先用户 key
    if provider in keys:
        return keys[provider]

    # fallback 公共 key
    if provider == "groq":
        return GROQ_API_KEY
    elif provider == "grok":
        return GROK_API_KEY
    elif provider == "gemini":
        return GEMINI_API_KEY

    return None


# =========================
# 🧠 获取客户端
# =========================
def get_client(provider, api_key):
    if not api_key:
        raise ValueError(f"{provider} API Key 未配置")

    if provider == "gemini":
        return genai.Client(api_key=api_key)

    elif provider == "grok":
        return OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )

    elif provider == "groq":
        return OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

    else:
        raise ValueError(f"未知 provider: {provider}")


# =========================
# ✨ 主函数
# =========================
def generate_reply(user_input, user_id, use_memory=True):
    # ===== 1. 状态 & 记忆 =====
    state = get_state(user_id)
    memory = get_memory(user_id) if use_memory else "（单次提问模式）"

    # 限制 memory 长度（防炸）
    if len(memory) > 2000:
        memory = memory[-2000:]

    # ===== 2. 模型配置 =====
    model_key = user_model.get(user_id, "fast")

    if model_key in DEFAULT_MODELS:
        model_key = DEFAULT_MODELS[model_key]

    config = MODEL_LIST.get(model_key, MODEL_LIST["groq_fast"])

    provider = config["api"]
    model_name = config["model"]

    # ===== 3. prompt 拆分 =====
    system_prompt = get_prompt(state, memory, "")
    user_prompt = user_input

    # ===== 4. 调用 =====
    try:
        return call_model(
            provider,
            model_name,
            user_id,
            system_prompt,
            user_prompt
        )

    except Exception as e:
        # ===== fallback =====
        if provider != "groq":
            try:
                return call_model(
                    "groq",
                    MODEL_LIST["groq_fast"]["model"],
                    user_id,
                    system_prompt,
                    user_prompt
                )
            except:
                pass

        return handle_error(e)


# =========================
# 🤖 调用模型
# =========================
def call_model(provider, model_name, user_id, system_prompt, user_prompt):
    api_key = get_api_key(user_id, provider)
    client = get_client(provider, api_key)

    # ===== Gemini =====
    if provider == "gemini":
        response = client.models.generate_content(
            model=model_name,
            contents=[{
                "role": "user",
                "parts": [system_prompt + "\n\n" + user_prompt]
            }]
        )
        return response.text

    # ===== OpenAI协议（Groq / Grok）=====
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8
    )

    return response.choices[0].message.content


# =========================
# ❌ 错误处理
# =========================
def handle_error(e):
    err = str(e).lower()
    full = str(e)[:300]

    if "401" in err or "unauthorized" in err:
        msg = "「能量块验证失败了…检查一下 /setkey 吧！」"

    elif "403" in err:
        msg = "「这个模型本姑娘用不了呢…换一个试试？」"

    elif "429" in err:
        msg = "「问太多啦，本姑娘脑子有点累…等会儿再来！」"

    elif "model" in err:
        msg = "「这个模型好像不存在呢，用 /model 看看支持哪些吧！」"

    else:
        msg = "（相机卡住了…）「呜，信号不太好呢…」"

    return f"{msg}\n\n(调试信息: {full})"