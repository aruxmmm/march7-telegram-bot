from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.state import get_state, user_model, user_state
from core.memory import memory_db
from core.llm import generate_reply
from core.memory import update_memory
from config import user_keys
from config import MODEL_LIST, DEFAULT_MODELS
from handlers.help import help_cmd

# 导入数据库函数
try:
    from core.database import get_user_api_keys, set_user_api_key, set_user_api_provider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


async def set_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if update.effective_chat.type != "private":
        await update.message.reply_text("（小声）「这种私密的事情，来私聊本姑娘再说啦！万一被别人看见你的能量块（Token）怎么办！」")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "用法错误呢～请告诉本姑娘你要配置哪个 API 的密钥：\n\n"
            "<b>Groq:</b> <code>/setkey groq gsk_xxxxxx</code>\n"
            "<b>Gemini:</b> <code>/setkey gemini AI_xxxxxx</code>\n"
            "<b>Grok (xAI):</b> <code>/setkey grok xai-xxxxxx</code>\n\n"
            "开拓者，可以同时配置多个哦！",
            parse_mode="HTML"
        )
        return

    api_type = context.args[0].lower()
    new_key = context.args[1]
    
    if api_type == "groq":
        if new_key.startswith("gsk_"):
            if DB_AVAILABLE:
                set_user_api_key(user_id, "groq", new_key)
            if user_id not in user_keys:
                user_keys[user_id] = {}
            if not isinstance(user_keys[user_id], dict):
                user_keys[user_id] = {}
            user_keys[user_id]["groq"] = new_key
            await update.message.reply_text("「好咧！本姑娘已经记住你的 Groq 能量块了～」")
        else:
            await update.message.reply_text("「唔...这个 Groq Key 看起来怪怪的，真的没填错吗？」")
    
    elif api_type == "gemini":
        if len(new_key) > 20:
            if DB_AVAILABLE:
                set_user_api_key(user_id, "gemini", new_key)
            if user_id not in user_keys:
                user_keys[user_id] = {}
            if not isinstance(user_keys[user_id], dict):
                user_keys[user_id] = {}
            user_keys[user_id]["gemini"] = new_key
            await update.message.reply_text("「好咧！本姑娘已经记住你的 Gemini 能量块了～」")
        else:
            await update.message.reply_text("「唔...这个 Gemini Key 看起来怪怪的，真的没填错吗？」")
    
    elif api_type == "grok":          # ← 新增 Grok 支持
        if new_key.startswith("xai-"):
            if DB_AVAILABLE:
                set_user_api_key(user_id, "grok", new_key)
            if user_id not in user_keys:
                user_keys[user_id] = {}
            if not isinstance(user_keys[user_id], dict):
                user_keys[user_id] = {}
            user_keys[user_id]["grok"] = new_key
            await update.message.reply_text("「好咧！本姑娘已经记住你的 Grok (xAI) 能量块了～ 三月七最强形态已就绪！」")
        else:
            await update.message.reply_text("「唔...这个 Grok Key 看起来怪怪的，应该是以 xai- 开头的哦～」")
    
    else:
        await update.message.reply_text("「本姑娘还没装那个 API 的驱动呢！现在支持 groq、gemini、grok 哦～」")


# 下面几个函数基本不变，只保留必要部分（已确认无冲突）
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("(跳到你面前，举起相机) 「咔嚓！嘿嘿，新朋友的样子记录下来啦！」")
    await help_cmd(update, context)

async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = " ".join(context.args)
    if not user_input:
        await update.message.reply_text("「提问也要带上内容哦，不然本姑娘猜不到呢！」")
        return
    reply_text = generate_reply(user_input, update.message.from_user.id, use_memory=False)
    await update.message.reply_text(f"<b>[单次提问]</b>\n{reply_text}", parse_mode=ParseMode.HTML)

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.memory import clear_memory
    user_id = update.message.from_user.id
    
    # 默认行为：重置记忆和状态
    if user_id in memory_db:
        memory_db[user_id] = ""
    user_state[user_id] = {"affinity": 0, "emotion": "开心"}
    if DB_AVAILABLE:
        from core.database import clear_user_memory, update_user_state
        clear_memory(user_id)
        update_user_state(user_id, 0, "开心")
    await update.message.reply_text("(清空了相册) 「呼...虽然有点舍不得，但我们要重新开始咯！」")

async def resetquota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """重置为使用公共额度"""
    user_id = update.message.from_user.id
    
    if DB_AVAILABLE:
        from core.database import reset_user_to_public_quota
        reset_user_to_public_quota(user_id)
    else:
        # 回退到内存中的操作
        from config import user_api_provider, user_keys
        if user_id in user_api_provider:
            del user_api_provider[user_id]
        if user_id in user_keys:
            del user_keys[user_id]
    await update.message.reply_text("(清空了私密配置) 「所有个人密钥已删除，现在使用公共额度啦～」")

def prettify_model_name(model_name: str) -> str:
    parts = model_name.split("-")
    formatted = []
    for part in parts:
        if part.isupper() or part.isdigit():
            formatted.append(part)
        elif part.replace('.', '', 1).isdigit():
            formatted.append(part)
        else:
            formatted.append(part.capitalize())
    return " ".join(formatted)


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import MODEL_LIST, DEFAULT_MODELS
    
    user_id = update.message.from_user.id
    
    if not context.args:
        help_text, reply_markup = build_provider_menu(user_id)
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return
    
    m = context.args[0].lower()
    if m in MODEL_LIST:
        user_model[user_id] = m
        if DB_AVAILABLE:
            from core.database import set_user_model
            set_user_model(user_id, m)
        api_type = MODEL_LIST[m]["api"]
        real_model = MODEL_LIST[m]["model"]
        await update.message.reply_text(
            f"切换成功！本姑娘现在用 {api_type.upper()} 的 <b>{m}</b>（{real_model}）模式呢～",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("「本姑娘还没装那个模型呢！用 /model 查看可用的哦～」")


def build_provider_menu(user_id: int):
    current_model_key = user_model.get(user_id, "fast")
    current_real_model = DEFAULT_MODELS.get(current_model_key, current_model_key)
    current_api = MODEL_LIST.get(current_real_model, MODEL_LIST["groq_fast"])["api"].upper()
    current_model_name = prettify_model_name(MODEL_LIST.get(current_real_model, MODEL_LIST["groq_fast"])["model"])

    help_text = (
        "请选择希望使用的 API 供应商：\n\n"
        f"当前模型：<b>{current_api} {current_model_name}</b>\n\n"
       
    )
    keyboard = [
        [InlineKeyboardButton("Groq", callback_data="model_api:groq")],
        [InlineKeyboardButton("Gemini", callback_data="model_api:gemini")],
        [InlineKeyboardButton("Grok", callback_data="model_api:grok")],
        [InlineKeyboardButton("取消 ❌", callback_data="model_cancel")],
    ]
    return help_text, InlineKeyboardMarkup(keyboard)


def build_model_menu(provider: str):
    filtered = [k for k, v in MODEL_LIST.items() if v.get("api") == provider]
    if not filtered:
        return None, None

    help_text = (
        f"已选择 <b>{provider.upper()}</b>，现在请选择具体模型：\n\n"
        "点击想用的型号。"
    )
    keyboard = [
        [InlineKeyboardButton(prettify_model_name(MODEL_LIST[k]["model"]), callback_data=f"model_select:{k}")]
        for k in filtered
    ]
    keyboard.append([
        InlineKeyboardButton("返回 API 选择", callback_data="model_back"),
        InlineKeyboardButton("取消 ❌", callback_data="model_cancel")
    ])
    return help_text, InlineKeyboardMarkup(keyboard)


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    await query.answer()

    if data == "model_cancel":
        await query.edit_message_text("「已取消模型切换，保持当前设置不变喽～」")
        return

    if data == "model_back":
        help_text, reply_markup = build_provider_menu(query.from_user.id)
        await query.edit_message_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    if data.startswith("model_api:"):
        provider = data.split(":", 1)[1]
        help_text, reply_markup = build_model_menu(provider)
        if help_text is None:
            await query.edit_message_text("这个 API 目前没有可选的模型了。")
            return
        await query.edit_message_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    if data.startswith("model_select:"):
        selected_model = data.split(":", 1)[1]
        if selected_model not in MODEL_LIST:
            await query.edit_message_text("「这个模型好像不存在了，请重新 /model 选择一次～」")
            return

        user_id = query.from_user.id
        user_model[user_id] = selected_model
        if DB_AVAILABLE:
            from core.database import set_user_model, set_user_api_provider
            set_user_model(user_id, selected_model)
            set_user_api_provider(user_id, MODEL_LIST[selected_model]["api"])
        else:
            from config import user_api_provider
            user_api_provider[user_id] = MODEL_LIST[selected_model]["api"]

        api_type = MODEL_LIST[selected_model]["api"].upper()
        real_model = MODEL_LIST[selected_model]["model"]
        readable = prettify_model_name(real_model)

        await query.edit_message_text(
            f"切换成功！本姑娘现在用 {api_type} 的 <b>{readable}</b> 模式啦～",
            parse_mode=ParseMode.HTML
        )
        return

    await query.edit_message_text("「我听不懂这个按钮呐，重新 /model 试试吧～」")


