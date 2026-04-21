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
    from core.database import get_user_api_keys, set_user_api_key, get_user_api_provider, set_user_api_provider
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


async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """切换用户使用的 API 供应商"""
    from config import user_api_provider, DEFAULT_MODELS, MODEL_LIST
    
    user_id = update.effective_user.id
    
    if not context.args:
        if DB_AVAILABLE:
            current = get_user_api_provider(user_id)
        else:
            current = user_api_provider.get(user_id, "groq")
            
        await update.message.reply_text(
            f"「当前使用的是 {current.upper()} 的脑子呢～」\n\n"
            "要切换的话，告诉本姑娘呀：\n"
            "<code>/setapi groq</code>　<code>/setapi gemini</code>　<code>/setapi grok</code>",
            parse_mode="HTML"
        )
        return
    
    api_choice = context.args[0].lower()
    if api_choice not in ["groq", "gemini", "grok"]:      # ← 新增 grok
        await update.message.reply_text("「本姑娘还不认识这个 API 呢！现在支持 groq、gemini、grok 哦～」")
        return
    
    # 检查是否配置了该 API 的 Key
    if DB_AVAILABLE:
        user_api_keys = get_user_api_keys(user_id)
    else:
        user_api_keys = user_keys.get(user_id, {})
        
    if isinstance(user_api_keys, str):   # 旧格式兼容
        if api_choice == "groq":
            if DB_AVAILABLE:
                set_user_api_provider(user_id, "groq")
            user_api_provider[user_id] = "groq"
            user_model[user_id] = "fast"
            await update.message.reply_text(f"「切换成功！现在本姑娘用 Groq 的脑子想事情啦～」")
            return
        else:
            await update.message.reply_text(f"「唔...你还没给本姑娘配置 {api_choice.upper()} 的能量块呢～」")
            return
    
    if api_choice not in user_api_keys and not (api_choice == "groq" and isinstance(user_api_keys, str)):
        await update.message.reply_text(f"「唔...你还没给本姑娘配置 {api_choice.upper()} 的能量块呢，快用 /setkey {api_choice} xxx 告诉我吧～」")
        return
    
    # 保存切换
    if DB_AVAILABLE:
        set_user_api_provider(user_id, api_choice)
    user_api_provider[user_id] = api_choice
    user_model[user_id] = "fast"
    
    await update.message.reply_text(f"「切换成功！现在本姑娘用 {api_choice.upper()} 的脑子想事情啦～」")


# 下面几个函数基本不变，只保留必要部分（已确认无冲突）
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

async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import MODEL_LIST
    
    user_id = update.message.from_user.id
    
    if not context.args:
        groq_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "groq"]
        gemini_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "gemini"]
        grok_models = [k for k, v in MODEL_LIST.items() if v.get("api") == "grok"]   # ← 新增
        
        help_text = "「本姑娘的脑子有这么几种啦～」\n\n"
        if groq_models:
            help_text += f"<b>Groq:</b> {', '.join(groq_models)}\n"
        if gemini_models:
            help_text += f"<b>Gemini:</b> {', '.join(gemini_models)}\n"
        if grok_models:
            help_text += f"<b>Grok (xAI):</b> {', '.join(grok_models)}\n\n"
        help_text += "用法：<code>/model groq_fast</code>\n<code>/model gemini_fast</code>\n <code>/model grok_fast</code> \n或其他型号～"
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
        return
    
    m = context.args[0].lower()
    if m in MODEL_LIST:
        user_model[user_id] = m
        if DB_AVAILABLE:
            from core.database import set_user_model
            set_user_model(user_id, m)
        api_type = MODEL_LIST[m]["api"]
        await update.message.reply_text(f"切换成功！本姑娘现在用 {api_type.upper()} 的 <b>{m}</b> 模式呢～", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("「本姑娘还没装那个模型呢！用 /model 查看可用的哦～」")


