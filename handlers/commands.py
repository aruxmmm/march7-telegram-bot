from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.state import get_state, user_model, user_state
from core.memory import memory_db
from core.llm import generate_reply
from core.memory import update_memory
from config import user_keys

# 导入数据库函数
try:
    from core.database import get_user_api_keys, set_user_api_key, get_user_api_provider, set_user_api_provider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

async def set_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 安全检查：防止在群聊里泄露 Token
    if update.effective_chat.type != "private":
        await update.message.reply_text("（小声）「这种私密的事情，来私聊本姑娘再说啦！万一被别人看见你的能量块（Token）怎么办！」")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "用法错误呢～请告诉本姑娘你要配置哪个 API 的密钥：\n\n"
            "<b>Groq:</b> <code>/setkey groq gsk_xxxxxx</code>\n"
            "<b>Gemini:</b> <code>/setkey gemini AI_xxxxxx</code>\n\n"
            "开拓者，可以同时配置多个哦！",
            parse_mode="HTML"
        )
        return

    api_type = context.args[0].lower()
    new_key = context.args[1]
    
    if api_type == "groq":
        if new_key.startswith("gsk_"):
            # 保存到数据库
            if DB_AVAILABLE:
                set_user_api_key(user_id, "groq", new_key)
            # 同时保存到内存以保证兼容性
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
            # 保存到数据库
            if DB_AVAILABLE:
                set_user_api_key(user_id, "gemini", new_key)
            # 同时保存到内存以保证兼容性
            if user_id not in user_keys:
                user_keys[user_id] = {}
            if not isinstance(user_keys[user_id], dict):
                user_keys[user_id] = {}
            user_keys[user_id]["gemini"] = new_key
            await update.message.reply_text("「好咧！本姑娘已经记住你的 Gemini 能量块了～」")
        else:
            await update.message.reply_text("「唔...这个 Gemini Key 看起来怪怪的，真的没填错吗？」")
    else:
        await update.message.reply_text("「本姑娘还没装那个 API 的驱动呢！现在只支持 groq 和 gemini 哦～」")

async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换用户使用的 API 供应商"""
    from core.state import user_model
    from config import user_api_provider, DEFAULT_MODELS, MODEL_LIST
    
    user_id = update.effective_user.id
    
    if not context.args:
        # 从数据库获取当前 API，失败则从内存获取
        if DB_AVAILABLE:
            current = get_user_api_provider(user_id)
        else:
            current = user_api_provider.get(user_id, "groq")
            
        await update.message.reply_text(
            f"「当前使用的是 {current.upper()} 的脑子呢～」\n\n"
            "要切换的话，告诉本姑娘呀：\n"
            "<code>/setapi groq</code> 或 <code>/setapi gemini</code>",
            parse_mode="HTML"
        )
        return
    
    api_choice = context.args[0].lower()
    if api_choice not in ["groq", "gemini"]:
        await update.message.reply_text("「本姑娘还不认识这个 API 呢！只有 groq 和 gemini 哦～」")
        return
    
    # 检查是否配置了该 API
    if DB_AVAILABLE:
        user_api_keys = get_user_api_keys(user_id)
    else:
        user_api_keys = user_keys.get(user_id, {})
        
    if isinstance(user_api_keys, str):
        # 兼容旧格式（全是 Groq Key）
        if api_choice == "groq":
            if DB_AVAILABLE:
                set_user_api_provider(user_id, "groq")
            user_api_provider[user_id] = "groq"
            user_model[user_id] = "fast"  # 重置为该 API 的默认模型
            await update.message.reply_text(f"「切换成功！现在本姑娘用 Groq 的脑子想事情啦～」")
            return
        else:
            await update.message.reply_text(f"「唔...你还没给本姑娘配置 Gemini 的能量块呢，快用 /setkey gemini xxx 告诉我吧～」")
            return
    
    if api_choice not in user_api_keys:
        await update.message.reply_text(f"「唔...你还没给本姑娘配置 {api_choice.upper()} 的能量块呢，快用 /setkey {api_choice} xxx 告诉我吧～」")
        return
    
    # 保存到数据库
    if DB_AVAILABLE:
        set_user_api_provider(user_id, api_choice)
    # 同时保存到内存以保证兼容性
    user_api_provider[user_id] = api_choice
    # 重置为选定 API 的默认模型
    user_model[user_id] = "fast"
    await update.message.reply_text(f"「切换成功！现在本姑娘用 {api_choice.upper()} 的脑子想事情啦～」")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import user_api_provider
    
    user_id = update.effective_user.id
    state = get_state(user_id)  # 获取当前好感度等状态

    # 判断 API 和 Key 来源状态
    # 优先从数据库读取
    if DB_AVAILABLE:
        current_api = get_user_api_provider(user_id).upper()
        user_api_keys_db = get_user_api_keys(user_id)
        if user_api_keys_db:
            apis = list(user_api_keys_db.keys())
            key_status = f"个人私有 ({', '.join([x.upper() for x in apis])})"
        else:
            key_status = "公共额度 (默认)"
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

    help_text = (
        "<b>March 7th Terminal</b>\n"
        "嘿嘿，开拓者！本姑娘已经准备好拍照啦～📷\n\n"

        "<b>┃ 菜单功能说明：</b>\n"
        "• <b>/start</b> - 📸 唤醒本姑娘\n"
        "• <b>/help</b> - 😘 显示这个超级棒的菜单\n"
        "• <b>/aris</b> - 😽 开启长对话模式\n"
        "• <b>/ask</b> - 🤸 快捷提问（不计入记忆）\n"
        "• <b>/setkey</b> - 🔑 配置你自己的 API Token\n"
        "• <b>/setapi</b> - 🔌 切换 API 提供商 (Groq更快/Gemini更聪明)\n"
        "• <b>/reset</b> - 🧩 重置我们的所有记忆\n"
        "• <b>/model</b> - 💎 切换本姑娘的大脑模型\n\n"
        "• <b>/stats</b> - 💾 查看本姑娘的统计数据\n\n"

        "<b>┃ 当前状态：</b>\n"
        f"• 运行模型：<code>{user_model.get(user_id, 'fast')}</code>\n"
        f"• API 提供商：<code>{current_api}</code>\n"
        f"• 好感等级：<code>{state['affinity']}</code>\n"
        f"• 能量来源：<code>{key_status}</code>\n\n"

        "<b>┃ 相关链接：</b>\n"
        "📦 <b>通知频道：</b> https://t.me/+f4F_N8BSzFJhZDll\n"
        "💬 <b>交流群组：</b> https://t.me/+GMfVNKY3vuNjOTA9"
    )

    # 创建交互按钮
    keyboard = [
        [
            InlineKeyboardButton("Groq Key 🔑", url="https://console.groq.com/keys"),
            InlineKeyboardButton("Gemini Key 🔑", url="https://makersuite.google.com/app/apikey")
        ],
        [
            InlineKeyboardButton("加入讨论群 💬", url="https://t.me/+GMfVNKY3vuNjOTA9")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 使用 HTML 模式发送
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("(跳到你面前，举起相机) 「咔嚓！嘿嘿，新朋友的样子记录下来啦！」")
    await help_cmd(update, context)

async def aris_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = " ".join(context.args)
    if not user_input:
        await update.message.reply_text("「你想和本姑娘聊什么呀？快说出来嘛！」")
        return
    reply_text = generate_reply(user_input, update.message.from_user.id)
    update_memory(update.message.from_user.id, f"用户: {user_input}\n三月七: {reply_text}")
    await update.message.reply_text(reply_text)

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
    
    # 清空内存中的数据
    if user_id in memory_db:
        memory_db[user_id] = ""
    user_state[user_id] = {"affinity": 0, "emotion": "开心"}
    
    # 清空数据库中的数据
    if DB_AVAILABLE:
        from core.database import clear_user_memory, update_user_state
        clear_memory(user_id)
        update_user_state(user_id, 0, "开心")
    
    await update.message.reply_text("(清空了相册) 「呼...虽然有点舍不得，但我们要重新开始咯！」")

async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import MODEL_LIST, user_api_provider
    
    user_id = update.message.from_user.id
    current_api = user_api_provider.get(user_id, "groq")
    
    if not context.args:
        # 显示可用的模型
        groq_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "groq"]
        gemini_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "gemini"]
        
        help_text = "「本姑娘的脑子有这么几种啦～」\n\n"
        if groq_models:
            help_text += f"<b>Groq:</b> {', '.join(groq_models)}\n"
        if gemini_models:
            help_text += f"<b>Gemini:</b> {', '.join(gemini_models)}\n\n"
        help_text += "用法：<code>/model groq_fast</code> 或其他型号～"
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
        return
    
    m = context.args[0].lower()
    if m in MODEL_LIST:
        user_model[user_id] = m
        # 保存到数据库
        if DB_AVAILABLE:
            from core.database import set_user_model
            set_user_model(user_id, m)
        api_type = MODEL_LIST[m]["api"]
        await update.message.reply_text(f"切换成功！本姑娘现在用 {api_type.upper()} 的 <b>{m}</b> 模式呢～", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("「本姑娘还没装那个模型呢！用 /model 查看可用的哦～」")