from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.state import get_state, user_model
from config import user_keys, MODEL_LIST, DEFAULT_MODELS

# 导入数据库函数
try:
    from core.database import get_user_api_keys, get_user_api_provider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import user_api_provider
    
    user_id = update.effective_user.id
    state = get_state(user_id)
    
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

    # ===== ✅ 新增：统一模型 & API 显示（核心修复）=====
    model = user_model.get(user_id, "fast")

    # fast → groq_fast
    real_model = DEFAULT_MODELS.get(model, model)

    # 从模型反推 API（关键）
    api = MODEL_LIST.get(real_model, MODEL_LIST["groq_fast"])["api"].upper()

    # ===== 文本 =====
    help_text = (
        "<b>March 7th Terminal</b>\n"
        "嘿嘿，开拓者！本姑娘已经准备好拍照啦～📷\n\n"

        "<b>┃ 菜单功能说明：</b>\n"
        "• <b>/start</b> - 📸 唤醒本姑娘\n"
        "• <b>/help</b> - 😘 显示这个超级棒的菜单\n"
        "• <b>/aris</b> - 😽 开启长对话模式\n"
        "• <b>/ask</b> - 🤸 快捷提问（不计入记忆）\n"
        "• <b>/setkey</b> - 🔑 配置你自己的 API Token\n"
        "• <b>/setapi</b> - 🔌 切换 API 提供商 (Groq/Gemini/Grok)\n"
        "• <b>/reset</b> - 🧩 重置我们的所有记忆\n"
        "• <b>/resetquota</b> - 💸 重置为使用公共额度\n"
        "• <b>/model</b> - 💎 切换本姑娘的大脑模型\n\n"
        "• <b>/stats</b> - 💾 查看本姑娘的统计数据\n\n"

        "<b>┃ 当前状态：</b>\n"
        f"• 运行模型：<code>{real_model}</code>\n"
        f"• API 提供商：<code>{api}</code>\n"
        f"• 好感等级：<code>{state['affinity']}</code>\n"
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
