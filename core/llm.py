from openai import OpenAI
from google import genai
from core.state import user_model, get_state, apply_model_state_update
from core.memory import get_memory
from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROK_API_KEY,
    AGNES_API_KEY,
    AGNES_BASE_URL,
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    MODEL_LIST,
    DEFAULT_MODELS,
    user_keys
)
import base64
import importlib
import logging
import re
from collections.abc import Callable, Iterable
from core.state import get_prompt_name

logger = logging.getLogger(__name__)

_STATE_MARKER = re.compile(
    r"\s*\[\[\s*affinity\s*:\s*([+-]\d+)\s*;\s*emotion\s*:\s*([^\]\r\n;]{1,20})\s*\]\]\s*$"
)


def finalize_reply(reply_text, user_id, state_baseline=None):
    """移除模型的状态标记，并在通过校验后写入用户状态。"""
    if not isinstance(reply_text, str):
        return reply_text

    match = _STATE_MARKER.search(reply_text)
    if not match:
        return reply_text

    affinity_delta = int(match.group(1))
    if not -10 <= affinity_delta <= 10:
        return reply_text

    apply_model_state_update(user_id, affinity_delta, match.group(2), state_baseline)
    return reply_text[:match.start()].rstrip()


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
    elif provider == "ollama":
        return OLLAMA_API_KEY
    elif provider == "agnes":
        return AGNES_API_KEY

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

    elif provider == "ollama":
        return OpenAI(
            api_key=api_key,
            base_url=OLLAMA_BASE_URL
        )

    elif provider == "agnes":
        return OpenAI(
            api_key=api_key,
            base_url=AGNES_BASE_URL
        )

    else:
        raise ValueError(f"未知 provider: {provider}")


# =========================
# ✨ 主函数
# =========================
def generate_reply(
    user_input,
    user_id,
    use_memory=True,
    image_data=None,
    image_mime_type="image/jpeg",
    state_baseline=None,
):
    provider, model_name, system_prompt, user_prompt = _build_reply_context(
        user_input,
        user_id,
        use_memory,
        image_data,
    )

    # ===== 4. 调用 =====
    try:
        reply_text = call_model(
            provider,
            model_name,
            user_id,
            system_prompt,
            user_prompt,
            image_data,
            image_mime_type,
        )
        return finalize_reply(reply_text, user_id, state_baseline)

    except Exception as e:
        # ===== fallback =====
        if provider != "groq":
            try:
                reply_text = call_model(
                    "groq",
                    MODEL_LIST["groq_fast"]["model"],
                    user_id,
                    system_prompt,
                    user_prompt,
                    image_data,
                    image_mime_type,
                )
                return finalize_reply(reply_text, user_id, state_baseline)
            except Exception:
                logger.exception("Groq fallback failed after the primary model failed")

        return handle_error(e)


def _build_reply_context(user_input, user_id, use_memory, image_data):
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
    # 根据用户选择动态加载 prompt 模块（例如 prompt.march7）
    prompt_name = get_prompt_name(user_id) if 'user_id' in locals() or True else 'march7'
    try:
        prompt_mod = importlib.import_module(f"prompt.{prompt_name}")
        system_prompt = prompt_mod.get_prompt(state, memory, "")
    except Exception:
        # 回退到默认的 march7 prompt
        try:
            prompt_mod = importlib.import_module("prompt.march7")
            system_prompt = prompt_mod.get_prompt(state, memory, "")
        except Exception as e:
            raise e
    if image_data:
        system_prompt += (
            "\n\n【图片回复】请遵循当前角色设定的性格和说话方式来观察、描述图片，"
            "不要切换成通用的客观解说口吻。用户只发图片或只让你描述图片时，"
            "不要用‘画面中’‘图中是’‘这张照片里’等说法开头或充当句子主语，"
            "直接从具体的人、物、动作或你的即时反应说起，再自然接上一句符合角色性格的评价、反应或好奇；"
            "可以针对具体细节提问，但不要每次都问，也不要只像图像识别报告一样罗列物体。"
            "不要编造图片里看不出的信息；用户附带了问题时，优先回答问题，不要硬加闲聊。"
        )
    return provider, model_name, system_prompt, user_input


def generate_reply_stream(
    user_input,
    user_id,
    on_chunk: Callable[[str], None],
    on_reset: Callable[[], None],
    use_memory=True,
    image_data=None,
    image_mime_type="image/jpeg",
    state_baseline=None,
) -> str:
    """Generate a reply while forwarding text chunks as the model produces them."""
    provider, model_name, system_prompt, user_prompt = _build_reply_context(
        user_input,
        user_id,
        use_memory,
        image_data,
    )

    try:
        reply_text = call_model_stream(
            provider,
            model_name,
            user_id,
            system_prompt,
            user_prompt,
            on_chunk,
            image_data,
            image_mime_type,
        )
        if not isinstance(reply_text, str):
            raise TypeError("The model returned a non-text response")
        return finalize_reply(reply_text, user_id, state_baseline)

    except Exception as e:
        if provider != "groq":
            try:
                on_reset()
                reply_text = call_model_stream(
                    "groq",
                    MODEL_LIST["groq_fast"]["model"],
                    user_id,
                    system_prompt,
                    user_prompt,
                    on_chunk,
                    image_data,
                    image_mime_type,
                )
                if not isinstance(reply_text, str):
                    raise TypeError("The fallback model returned a non-text response")
                return finalize_reply(reply_text, user_id, state_baseline)
            except Exception:
                logger.exception("Groq streaming fallback failed after the primary model failed")

        return handle_error(e)


# =========================
# 🤖 调用模型
# =========================
def call_model(provider, model_name, user_id, system_prompt, user_prompt, image_data=None, image_mime_type="image/jpeg"):
    api_key = get_api_key(user_id, provider)
    client = get_client(provider, api_key)

    # ===== Gemini =====
    if provider == "gemini":
        contents = system_prompt + "\n\n" + user_prompt
        if image_data:
            from google.genai import types
            contents = [
                contents,
                types.Part.from_bytes(data=image_data, mime_type=image_mime_type),
            ]
        response = client.models.generate_content(
            model=model_name,
            contents=contents
        )
        return response.text

    # ===== OpenAI 兼容协议 =====
    user_content = user_prompt
    if image_data:
        encoded_image = base64.b64encode(image_data).decode("ascii")
        user_content = [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime_type};base64,{encoded_image}"},
            },
        ]
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.8
    )

    return response.choices[0].message.content


def call_model_stream(
    provider,
    model_name,
    user_id,
    system_prompt,
    user_prompt,
    on_chunk: Callable[[str], None],
    image_data=None,
    image_mime_type="image/jpeg",
) -> str:
    api_key = get_api_key(user_id, provider)
    client = get_client(provider, api_key)

    if provider == "gemini":
        contents = system_prompt + "\n\n" + user_prompt
        if image_data:
            from google.genai import types
            contents = [
                contents,
                types.Part.from_bytes(data=image_data, mime_type=image_mime_type),
            ]
        generate_content_stream = getattr(client.models, "generate_content_stream", None)
        if not callable(generate_content_stream):
            raise RuntimeError("Installed Google GenAI client does not support content streaming")
        chunks = generate_content_stream(
            model=model_name,
            contents=contents,
        )
        if not isinstance(chunks, Iterable):
            raise TypeError("Google GenAI returned a non-iterable streaming response")
        parts = []
        for chunk in chunks:
            text = chunk.text
            if text:
                parts.append(text)
                on_chunk(text)
        return "".join(parts)

    user_content = user_prompt
    if image_data:
        encoded_image = base64.b64encode(image_data).decode("ascii")
        user_content = [
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_mime_type};base64,{encoded_image}"},
            },
        ]

    chat_api = getattr(client, "chat", None)
    completions_api = getattr(chat_api, "completions", None)
    create_completion = getattr(completions_api, "create", None)
    if not callable(create_completion):
        raise RuntimeError(f"Provider {provider} does not support chat completion streaming")

    chunks = create_completion(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.8,
        stream=True,
    )
    if not isinstance(chunks, Iterable):
        raise TypeError(f"Provider {provider} returned a non-iterable streaming response")

    parts = []
    for chunk in chunks:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content
        if isinstance(text, str) and text:
            parts.append(text)
            on_chunk(text)
    return "".join(parts)


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

    elif "model" in err and any(
        phrase in err for phrase in ("not found", "does not exist", "unsupported", "invalid model")
    ):
        msg = "「这个模型好像不存在呢，用 /model 看看支持哪些吧！」"

    else:
        msg = "（相机卡住了…）「呜，信号不太好呢…」"

    return f"{msg}\n\n(调试信息: {full})"