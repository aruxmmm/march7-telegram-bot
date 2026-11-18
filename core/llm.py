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
_STICKER_MARKER = re.compile(
    r"\[\[\s*sticker\s*:\s*(\d+)\s*\]\]",
    re.IGNORECASE,
)
_EXPLICIT_STICKER_REQUEST = re.compile(
    r"(?:给我|帮我|请)?\s*(?:发|发送|来)\s*(?:我)?\s*(?:一个|一张|个|张)?"
    r"\s*(?:三月七)?(?:的)?\s*(?:贴纸|表情包)"
    r"|(?:贴纸|表情包).{0,6}(?:发一个|发一张|来一个|来一张|给我)"
    r"|\b(?:send|give)\s+(?:me\s+)?(?:a\s+)?(?:sticker|sticker pack)\b",
    re.IGNORECASE,
)
_EXPLICIT_STICKER_OPT_OUT = re.compile(
    r"(?:不要|别|不用|不需要|不想要).{0,8}(?:发|发送|贴纸|表情包)"
    r"|(?:don't|do not)\s+(?:send|give me)\s+(?:a\s+)?sticker",
    re.IGNORECASE,
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


def _finalize_generated_reply(
    reply_text,
    user_id,
    state_baseline,
    on_sticker,
    user_input,
):
    if not isinstance(reply_text, str):
        return finalize_reply(reply_text, user_id, state_baseline)

    matches = list(_STICKER_MARKER.finditer(reply_text))
    sticker_index = next(
        (int(match.group(1)) for match in matches if 0 <= int(match.group(1)) < 16),
        None,
    )
    if isinstance(user_input, str) and _EXPLICIT_STICKER_OPT_OUT.search(user_input):
        if sticker_index is not None:
            logger.warning("Model selected a sticker despite the user's explicit opt-out")
        sticker_index = None
    elif (
        sticker_index is None
        and isinstance(user_input, str)
        and _EXPLICIT_STICKER_REQUEST.search(user_input)
    ):
        sticker_index = 15
        logger.warning(
            "Model omitted the sticker marker for an explicit request; using fallback sticker index=%s",
            sticker_index,
        )

    if matches:
        reply_text = _STICKER_MARKER.sub("", reply_text).strip()
    if sticker_index is not None and on_sticker:
        on_sticker(sticker_index)
    return finalize_reply(reply_text, user_id, state_baseline)


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
    on_sticker: Callable[[int], None] | None = None,
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
        return _finalize_generated_reply(
            reply_text, user_id, state_baseline, on_sticker, user_input
        )

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
                return _finalize_generated_reply(
                    reply_text, user_id, state_baseline, on_sticker, user_input
                )
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
    system_prompt += """

【表情包发送决策】
你要根据当前对话决定是否发送一张三月七表情包,不要频繁发送表情包。用户明确要求发贴纸或表情包时，必须发送一张最合适的贴纸；用户明确说不要贴纸时，不要发送。其他情况下，只有在贴纸能自然加强互动时才发送；普通问答、严肃或敏感话题、发送会显得突兀时不要发送。
若决定发送，请在正常回复后另起一行输出一个控制标记，格式必须严格为 [[sticker:N]]，N 为以下编号之一；只能选择一张：
0：拍照俏皮眨眼；1：分享糖果、温柔安慰；2：兴奋欢呼；3：拿相机害羞；
4：点赞认可；5：开心戴爱心墨镜；6：闭眼平静微笑；7：兴奋展示战利品；
8：唱歌热情回应；9：哭泣委屈；10：紧张冒汗；11：生气嘟嘴；
12：生日蛋糕庆祝；13：举相机拍照；14：疲惫犯困；15：可爱开心举手。
控制标记只供程序读取，不要解释或在回复正文中展示；若有好感度/情绪标记，sticker 标记必须放在它之前。不发送贴纸时不要输出 sticker 标记。
"""
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
    on_sticker: Callable[[int], None] | None = None,
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
        return _finalize_generated_reply(
            reply_text, user_id, state_baseline, on_sticker, user_input
        )

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
                return _finalize_generated_reply(
                    reply_text, user_id, state_baseline, on_sticker, user_input
                )
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