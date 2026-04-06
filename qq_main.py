import hashlib
import hmac
import json
import logging
import re
import threading
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import (
    QQ_BOT_API_URL,
    QQ_BOT_ENABLED,
    QQ_BOT_PORT,
    QQ_BOT_SECRET,
    DEFAULT_MODELS,
    MODEL_LIST,
    user_api_provider,
    user_keys,
)
from core.llm import generate_reply
from core.memory import clear_memory, update_memory
from core.state import get_state, update_state, user_model, user_state

try:
    from core.database import (
        get_user_api_keys,
        set_user_api_key,
        get_user_api_provider,
        set_user_api_provider,
        update_user_state,
        set_user_model,
    )
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CQ_CODE_REGEX = re.compile(r"\[CQ:[^\]]+\]")
AT_CQ_REGEX = re.compile(r"\[CQ:at,qq=[0-9]+\]")
COMMAND_PREFIXES = ("/", "!", "！")


def _is_enabled():
    return QQ_BOT_ENABLED and bool(QQ_BOT_API_URL.strip())


def _verify_signature(body: bytes, headers) -> bool:
    if not QQ_BOT_SECRET:
        return True

    signature = headers.get("X-Signature", "")
    if not signature:
        return False

    expected = hmac.new(QQ_BOT_SECRET.encode("utf-8"), body, hashlib.sha1).hexdigest()
    return signature == expected or signature == f"sha1={expected}"


def _strip_cq_codes(text: str) -> str:
    return CQ_CODE_REGEX.sub("", text).strip()


def _is_direct_group_message(text: str) -> bool:
    return bool(AT_CQ_REGEX.search(text) or "三月七" in text or "本姑娘" in text or text.startswith(COMMAND_PREFIXES))


def _parse_command(text: str):
    text = text.strip()
    if not text:
        return None, []

    if text.startswith(COMMAND_PREFIXES):
        trimmed = text.lstrip("/！!")
        parts = trimmed.split()
        return parts[0].lower(), parts[1:]

    return None, []


def _send_onebot_request(payload: dict):
    api_url = QQ_BOT_API_URL.rstrip("/") + "/send_msg"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            logger.info("QQ Bot send_msg status=%s", resp.status)
            return True
    except urllib.error.HTTPError as err:
        logger.error("QQ Bot HTTP 错误：%s %s", err.code, err.reason)
    except urllib.error.URLError as err:
        logger.error("QQ Bot 请求失败：%s", err)
    except Exception as err:
        logger.exception("QQ Bot 发送消息异常：%s", err)
    return False


def _send_text(message_type: str, target_id: int, text: str):
    payload = {
        "message_type": message_type,
        "message": text,
    }
    if message_type == "private":
        payload["user_id"] = target_id
    else:
        payload["group_id"] = target_id
    return _send_onebot_request(payload)


def _get_user_api_keys(user_id):
    if DB_AVAILABLE:
        return get_user_api_keys(user_id) or {}
    return user_keys.get(user_id, {}) if isinstance(user_keys.get(user_id), dict) else user_keys.get(user_id, {})


def _get_user_api_provider(user_id):
    if DB_AVAILABLE:
        return get_user_api_provider(user_id)
    return user_api_provider.get(user_id, "groq")


def _set_user_api_key(user_id, api_type, key):
    if DB_AVAILABLE:
        set_user_api_key(user_id, api_type, key)
    if user_id not in user_keys or not isinstance(user_keys.get(user_id), dict):
        user_keys[user_id] = {}
    user_keys[user_id][api_type] = key


def _set_user_api_provider(user_id, provider):
    if DB_AVAILABLE:
        set_user_api_provider(user_id, provider)
    user_api_provider[user_id] = provider


def _set_user_model(user_id, model):
    if DB_AVAILABLE:
        set_user_model(user_id, model)
    user_model[user_id] = model


def _build_help_text(user_id: int) -> str:
    state = get_state(user_id)
    if DB_AVAILABLE:
        current_api = get_user_api_provider(user_id).upper()
        keys = get_user_api_keys(user_id)
    else:
        current_api = user_api_provider.get(user_id, "groq").upper()
        keys = _get_user_api_keys(user_id)

    if isinstance(keys, str):
        key_status = f"个人私有 (Groq)"
    elif isinstance(keys, dict) and keys:
        apis = ", ".join([x.upper() for x in keys.keys()])
        key_status = f"个人私有 ({apis})"
    else:
        key_status = "公共额度 (默认)"

    current_model = user_model.get(user_id, "fast")

    help_text = (
        "三月七已上线～\n"
        "你可以直接在私聊里使用以下命令：\n"
        "• /start - 唤醒本姑娘\n"
        "• /help - 查看帮助\n"
        "• /aris [内容] - 开始多轮对话\n"
        "• /ask [内容] - 单次快速问答\n"
        "• /setkey [groq|gemini] [key] - 配置 API Key\n"
        "• /setapi [groq|gemini] - 切换 API 供应商\n"
        "• /model [模型名] - 切换模型\n"
        "• /reset - 重置对话和状态\n\n"
        f"当前模型：{current_model}\n"
        f"当前 API：{current_api}\n"
        f"Key 状态：{key_status}\n"
        "注意：在群聊中请 @ 三月七 或使用命令前缀 / 才会触发回复。"
    )
    return help_text


def _handle_command(user_id: int, message_type: str, target_id: int, command: str, args: list[str]):
    command = command.lower()
    if command == "start":
        _send_text(message_type, target_id, "(跳到你面前，举起相机) 「咔嚓！嘿嘿，新朋友的样子记录下来啦！」")
        _send_text(message_type, target_id, _build_help_text(user_id))
        return

    if command == "help":
        _send_text(message_type, target_id, _build_help_text(user_id))
        return

    if command == "setkey":
        if message_type != "private":
            _send_text(message_type, target_id, "请在私聊中发送 /setkey groq gsk_xxx 或 /setkey gemini AI_xxx，以保护你的密钥安全。")
            return
        if len(args) < 2:
            _send_text(message_type, target_id, "用法：/setkey groq gsk_xxx 或 /setkey gemini AI_xxx")
            return
        api_type = args[0].lower()
        new_key = args[1]
        if api_type == "groq":
            if new_key.startswith("gsk_"):
                _set_user_api_key(user_id, "groq", new_key)
                _send_text(message_type, target_id, "好咧！本姑娘已经记住你的 Groq 能量块了～")
            else:
                _send_text(message_type, target_id, "这个 Groq Key 看起来不对，请检查是否为 gsk_xxx 格式。")
        elif api_type == "gemini":
            if len(new_key) > 20:
                _set_user_api_key(user_id, "gemini", new_key)
                _send_text(message_type, target_id, "好咧！本姑娘已经记住你的 Gemini 能量块了～")
            else:
                _send_text(message_type, target_id, "这个 Gemini Key 看起来不对，请检查是否正确。")
        else:
            _send_text(message_type, target_id, "本姑娘还没认识这个 API 哦，目前只支持 groq 和 gemini。")
        return

    if command == "setapi":
        if len(args) < 1:
            if DB_AVAILABLE:
                current_api = get_user_api_provider(user_id).upper()
            else:
                current_api = user_api_provider.get(user_id, "groq").upper()
            _send_text(message_type, target_id, f"当前 API：{current_api}\n用法：/setapi groq 或 /setapi gemini")
            return
        api_choice = args[0].lower()
        if api_choice not in ["groq", "gemini"]:
            _send_text(message_type, target_id, "本姑娘还不认识这个 API 呢！仅支持 groq 和 gemini。")
            return
        keys = _get_user_api_keys(user_id)
        if isinstance(keys, str):
            if api_choice == "groq":
                _set_user_api_provider(user_id, "groq")
                _set_user_model(user_id, "fast")
                _send_text(message_type, target_id, "切换成功！现在本姑娘用 Groq 的脑子想事情啦～")
                return
            _send_text(message_type, target_id, "你还没给本姑娘配置 Gemini Key 呢～请先使用 /setkey gemini AI_xxx")
            return
        if api_choice not in keys:
            _send_text(message_type, target_id, f"你还没配置 {api_choice.upper()} Key，请先用 /setkey {api_choice} key 绑定。")
            return
        _set_user_api_provider(user_id, api_choice)
        _set_user_model(user_id, "fast")
        _send_text(message_type, target_id, f"切换成功！现在本姑娘用 {api_choice.upper()} 的脑子想事情啦～")
        return

    if command == "aris":
        user_input = " ".join(args)
        if not user_input:
            _send_text(message_type, target_id, "你想和本姑娘聊什么呀？快说出来嘛！")
            return
        reply_text = generate_reply(user_input, user_id)
        update_memory(user_id, f"用户: {user_input}\n三月七: {reply_text}")
        _send_text(message_type, target_id, reply_text)
        return

    if command == "ask":
        user_input = " ".join(args)
        if not user_input:
            _send_text(message_type, target_id, "提问也要带上内容哦，不然本姑娘猜不到呢！")
            return
        reply_text = generate_reply(user_input, user_id, use_memory=False)
        _send_text(message_type, target_id, f"[单次提问] {reply_text}")
        return

    if command == "reset":
        clear_memory(user_id)
        user_state[user_id] = {"affinity": 0, "emotion": "开心"}
        if DB_AVAILABLE:
            update_user_state(user_id, 0, "开心")
        _send_text(message_type, target_id, "(清空了相册) 呼...虽然有点舍不得，但我们要重新开始咯！")
        return

    if command == "model":
        if len(args) < 1:
            groq_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "groq"]
            gemini_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "gemini"]
            help_text = "本姑娘的脑子有这么几种啦～\n"
            if groq_models:
                help_text += f"Groq: {', '.join(groq_models)}\n"
            if gemini_models:
                help_text += f"Gemini: {', '.join(gemini_models)}\n"
            help_text += "用法：/model groq_fast 或 /model gemini_fast"
            _send_text(message_type, target_id, help_text)
            return
        m = args[0].lower()
        if m in MODEL_LIST:
            _set_user_model(user_id, m)
            api_type = MODEL_LIST[m]["api"]
            _send_text(message_type, target_id, f"切换成功！本姑娘现在用 {api_type.upper()} 的 {m} 模式呢～")
        else:
            _send_text(message_type, target_id, "本姑娘还没装那个模型呢！用 /model 查看可用的哦～")
        return

    _send_text(message_type, target_id, "本姑娘暂时还没听懂你的命令哦～试试 /help 看看吧。")


def _handle_chat(user_id: int, message_type: str, target_id: int, message: str):
    if not message:
        return
    update_state(user_id, message)
    reply_text = generate_reply(message, user_id)
    update_memory(user_id, f"用户: {message}\n三月七: {reply_text}")
    _send_text(message_type, target_id, reply_text)


def _handle_event(event: dict):
    if event.get("post_type") != "message":
        return

    message_type = event.get("message_type")
    user_id = event.get("user_id")
    content = event.get("message", "")

    if message_type == "group":
        group_id = event.get("group_id")
        if not group_id:
            return
        if not _is_direct_group_message(content):
            return
        target_id = group_id
    else:
        target_id = user_id

    if not content or not user_id:
        return

    command, args = _parse_command(_strip_cq_codes(content))
    if command:
        _handle_command(user_id, message_type, target_id, command, args)
        return

    if message_type == "group" and not _is_direct_group_message(content):
        return

    cleaned_message = _strip_cq_codes(content)
    _handle_chat(user_id, message_type, target_id, cleaned_message)


class OneBotRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if not _verify_signature(body, self.headers):
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"error\": \"Invalid signature\"}")
            return

        try:
            event = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"error\": \"Invalid JSON\"}")
            return

        threading.Thread(target=_handle_event, args=(event,), daemon=True).start()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{\"status\": \"ok\"}")

    def log_message(self, format, *args):
        return


def start_qq_bot(block: bool = True):
    if not _is_enabled():
        logger.warning("QQ Bot 未启用，跳过 QQ 服务启动。")
        return

    server = ThreadingHTTPServer(("0.0.0.0", QQ_BOT_PORT), OneBotRequestHandler)
    logger.info("QQ Bot 已启动，监听端口 %s", QQ_BOT_PORT)

    if block:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("QQ Bot 已停止。")
    else:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server


if __name__ == "__main__":
    if not _is_enabled():
        logger.error("QQ Bot 未启用或缺少 QQ_BOT_API_URL，请检查 .env 配置。")
    else:
        start_qq_bot(block=True)
