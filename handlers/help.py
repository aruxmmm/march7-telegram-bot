from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ContextTypes
from core.state import get_state, user_model, get_prompt_name
from config import user_keys, MODEL_LIST, DEFAULT_MODELS

# 导入数据库函数
try:
    from core.database import get_user_api_keys, get_user_api_provider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import user_api_provider
    
    # 发送正在输入的状态指示符
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )
    
    user_id = update.effective_user.id
    state = get_state(user_id)
    current_prompt = get_prompt_name(user_id)
    
    # ===== 原有：Key / API 状态（不动）=====
    if DB_AVAILABLE:
        current_api = get_user_api_provider(user_id).upper()
        user_api_keys_db = get_user_api_keys(user_id)
        apis = list(user_api_keys_db.keys()) if user_api_keys_db else []
        key_status = f"个人私有 ({', '.join([x.upper() for x in apis])})" if apis else "公共额度 (默认)"
    else:
        current_api = user_api_provider.get(user_id, "groq").upper()
        user_api_keys = user_keys.get(user_id, {})
        if isinstance(user_api_keys, str):
            key_status = "个人私有 (Groq)"
        elif isinstance(user_api_keys, dict):
            apis = list(user_api_keys.keys())
            key_status = f"个人私有 ({', '.join([x.upper() for x in apis])})"
        else:
            key_status = "公共额度 (默认)"

    model = user_model.get(user_id, "groq_fast")
# 兼容旧 "fast"/"smart" key
    model = DEFAULT_MODELS.get(model, model)
# 如果还是不在 MODEL_LIST 里，拼 api_model 再试一次
    if model not in MODEL_LIST:
        if DB_AVAILABLE:
          api_provider = get_user_api_provider(user_id)
        else:
          api_provider = user_api_provider.get(user_id, "groq")
        model = f"{api_provider}_{model}" if f"{api_provider}_{model}" in MODEL_LIST else "groq_fast"
    real_model = MODEL_LIST[model]["model"]
    api = MODEL_LIST[model]["api"].upper()
    
    # ===== 文本 =====
    help_text = (
        "<b>March 7th Terminal</b>\n"
        "嘿嘿，开拓者！本姑娘已经准备好拍照啦～📷\n\n"

      
        "<b>命令</b>              <b>功能说明</b>\n"
     "────────────────────────────────────\n"
     "<code>/start</code> — 📸 唤醒本姑娘\n"
     "<code>/help</code> — 😘 显示这个超级棒的菜单\n"
     "<code>/ask</code> — 🤸 快捷提问，不占用记忆\n"
     "<code>/setkey</code> — 🔑 配置你自己的 API Token\n"
     "<code>/prompt</code> — 🎭 prompt 角色管理\n"
     "    • /prompt              查看当前 prompt 和可用列表\n"
     "    • /prompt list         查看可用 prompt\n"
     "    • /prompt show         预览当前 prompt\n"
        "    • /prompt show evernight  预览指定 prompt\n"
        "    • /prompt evernight       切换为 evernight 角色\n"
     "    • /prompt switch march7    切换回 march7 角色\n"
     "<code>/reset</code> — 🧩 清空记忆，重新开始\n"
    "<code>/memory</code> — 🧠 查看当前记忆\n"
     "<code>/resetquota</code> — 💸 重置为公共额度\n"
     "<code>/model</code> — 💎 切换本姑娘的大脑模型\n"
     "<code>/stats</code> — 💾 查看统计数据\n"
     "\n"

        "<b>┃ 当前状态：</b>\n"
        f"• 运行模型：<code>{real_model}</code>\n"
        f"• 当前角色：<code>{current_prompt}</code>\n"
        f"• API 提供商：<code>{api}</code>\n"
        f"• 能量来源：<code>{key_status}</code>\n\n"

        "<b>┃ 相关链接：</b>\n"
        "📦 <b>通知频道：</b> https://t.me/+f4F_N8BSzFJhZDll\n"
        "💬 <b>交流群组：</b> https://t.me/+GMfVNKY3vuNjOTA9"
    )

    # ===== 按钮（不动）=====
    keyboard = [
        [
            InlineKeyboardButton("Groq Key 🔑", url="https://console.groq.com/keys"),
            InlineKeyboardButton("Gemini Key 🔑", url="https://makersuite.google.com/app/apikey"),
            InlineKeyboardButton("Grok Key 🔑", url="https://console.x.ai/")
        ],
        [
            InlineKeyboardButton("加入讨论群 💬", url="https://t.me/+GMfVNKY3vuNjOTA9")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )
