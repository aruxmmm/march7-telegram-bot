import asyncio
from html import escape
import logging
import re
from telegram import Message, MessageEntity, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import EndPointNotFound
from telegram.ext import ContextTypes
from core.state import user_model, get_prompt_name
from config import user_keys, MODEL_LIST, DEFAULT_MODELS

logger = logging.getLogger(__name__)

# 导入数据库函数
try:
    from core.database import get_user_api_keys, get_user_api_provider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


def _help_entities(text):
    command_names = (
        "start", "help", "ask", "regenerate", "memory", "state", "reset",
        "prompt", "model", "setkey", "resetquota", "stats",
    )
    command_pattern = re.compile(
        rf"/(?:{'|'.join(command_names)})(?![A-Za-z0-9_])"
    )
    entities = []
    for match in command_pattern.finditer(text):
        offset = len(text[:match.start()].encode("utf-16-le")) // 2
        length = len(match.group().encode("utf-16-le")) // 2
        entities.append(MessageEntity("bot_command", offset, length))

    for heading in (
        "March 7th Terminal", "📚 聊天与记忆", "🎭 角色与模型",
        "🔑 账户与统计", "📊 当前状态",
    ):
        start = text.find(heading)
        if start >= 0:
            offset = len(text[:start].encode("utf-16-le")) // 2
            length = len(heading.encode("utf-16-le")) // 2
            entities.append(MessageEntity("bold", offset, length))

    return sorted(entities, key=lambda entity: entity.offset)


def _rich_help_html(text):
    headings = {
        "March 7th Terminal": "h1",
        "📚 聊天与记忆": "h2",
        "🎭 角色与模型": "h2",
        "🔑 账户与统计": "h2",
        "📊 当前状态": "h2",
    }
    blocks = []
    for line in text.splitlines():
        if not line:
            continue
        tag = headings.get(line)
        escaped_line = escape(line)
        blocks.append(f"<{tag}>{escaped_line}</{tag}>" if tag else f"<p>{escaped_line}</p>")
    return "".join(blocks)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import user_api_provider

    user_id = update.effective_user.id
    current_prompt = await asyncio.to_thread(get_prompt_name, user_id)
    
    # ===== API Key 状态 =====
    if DB_AVAILABLE:
        user_api_keys_db = await asyncio.to_thread(get_user_api_keys, user_id)
        apis = list(user_api_keys_db.keys()) if user_api_keys_db else []
        key_status = f"个人私有 ({', '.join([x.upper() for x in apis])})" if apis else "公共额度 (默认)"
    else:
        user_api_keys = user_keys.get(user_id, {})
        if isinstance(user_api_keys, str):
            key_status = "个人私有 (Groq)"
        elif isinstance(user_api_keys, dict):
            apis = list(user_api_keys.keys())
            key_status = f"个人私有 ({', '.join([x.upper() for x in apis])})"
        else:
            key_status = "公共额度 (默认)"

    model = user_model.get(user_id, "fast")
    # 兼容旧 "fast"/"smart" key
    model = DEFAULT_MODELS.get(model, model)
    # 如果还是不在 MODEL_LIST 里，拼 api_model 再试一次
    if model not in MODEL_LIST:
        if DB_AVAILABLE:
            api_provider = await asyncio.to_thread(get_user_api_provider, user_id)
        else:
            api_provider = user_api_provider.get(user_id, "agnes")
        model = f"{api_provider}_{model}" if f"{api_provider}_{model}" in MODEL_LIST else DEFAULT_MODELS["fast"]
    real_model = MODEL_LIST[model]["model"]
    api = MODEL_LIST[model]["api"].upper()
    
    # ===== 帮助内容 =====
    help_text = (
        "March 7th Terminal\n"
        "嘿嘿，开拓者！本姑娘已经准备好拍照啦～📷\n\n"
        "点按蓝色指令即可运行；需要参数的指令请在末尾补上参数。\n\n"
        "📚 聊天与记忆\n"
        "/start — 开始使用\n"
        "/help — 查看帮助\n"
        "/ask 问题 — 单次提问，不读写聊天记忆\n"
        "/regenerate — 重新生成本次运行中最近一条聊天回复\n"
        "/memory — 查看当前角色的聊天记忆\n"
        "/state — 查看好感度与情绪\n"
        "/reset — 清空聊天记忆并重置状态\n\n"
        "🎭 角色与模型\n"
        "/prompt — 查看角色并打开切换菜单\n"
        "/prompt list — 列出可用角色\n"
        "/prompt show [名称] — 预览当前或指定角色\n"
        "/prompt 名称 — 切换角色；也可用 /prompt switch 名称\n"
        "/model — 查看并切换模型\n"
        "/model 模型名 — 直接切换到指定模型\n\n"
        "🔑 账户与统计\n"
        "/setkey 提供商 密钥 — 设置个人 API Key（groq、gemini、grok、agnes）\n"
        "/resetquota — 删除个人 API Key，改用公共额度\n"
        "/stats — 查看使用统计\n\n"

        "📊 当前状态\n"
        f"• 运行模型：{real_model}\n"
        f"• 当前角色：{current_prompt}\n"
        f"• API 提供商：{api}\n"
        f"• 能量来源：{key_status}\n\n"


    )

    # ===== 按钮（不动）=====
    keyboard = [
        [
            InlineKeyboardButton("Groq Key 🔑", url="https://console.groq.com/keys"),
            InlineKeyboardButton("Gemini Key 🔑", url="https://makersuite.google.com/app/apikey"),
            InlineKeyboardButton("Grok Key 🔑", url="https://console.x.ai/"),
            InlineKeyboardButton("Agnes Key 🔑", url="https://www.agnes-ai.com/")
        ],
        [
            InlineKeyboardButton("加入讨论群 💬", url="https://t.me/+GMfVNKY3vuNjOTA9"),
            InlineKeyboardButton("加入通知频道 💬", url="https://t.me/+f4F_N8BSzFJhZDll ")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.do_api_request(
            "sendRichMessage",
            api_kwargs={
                "chat_id": update.effective_chat.id,
                "rich_message": {"html": _rich_help_html(help_text)},
                "reply_markup": reply_markup.to_dict(),
            },
            return_type=Message,
        )
    except EndPointNotFound:
        logger.warning("Telegram Bot API does not support rich messages; sending standard help text")
        await update.message.reply_text(
            help_text,
            entities=_help_entities(help_text),
            reply_markup=reply_markup,
        )
