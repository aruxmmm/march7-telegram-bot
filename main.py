import random
import logging
import os

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.constants import ParseMode
from openai import OpenAI

# ====== 用户配置存储 ======
user_keys = {}  # 格式: {user_id: "gsk_xxxx"}
user_model = {} # 原有的模型选择

# ====== 日志配置 ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== 配置区 ======
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY","")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN","")

# 调试检查：如果读不到变量，直接报错并提示
if not TELEGRAM_TOKEN:
    raise ValueError("错误：未检测到 TELEGRAM_TOKEN 环境变量！ 请检查Variables 设置。")
if not GROQ_API_KEY:
    raise ValueError("错误：未检测到 GROQ_API_KEY 环境变量！ 请检查Variables 设置")

print(f"Token 加载成功，长度为: {len(TELEGRAM_TOKEN)}") # 打印长度确认读到了

MODEL_LIST = {
    "fast": "llama-3.3-70b-versatile",
    "smart": "mixtral-8x7b-32768"
}

# 数据存储
user_model = {}
user_state = {}
memory_db = {}

def main():
    # 再次检查
    if not TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN:
        logger.error("无效的 TELEGRAM_TOKEN！请检查环境变量。")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    # ... 后续注册 handler 的逻辑 ...
    app.run_polling()

# ====== 初始化 Groq 客户端 ======
def get_mg_client(user_id):
    """根据用户 ID 获取对应的 Groq 客户端"""
    # 如果用户设置了自己的 Key，就用他的；否则用你代码里默认的 GROQ_API_KEY
    custom_key = user_keys.get(user_id)
    target_key = custom_key if custom_key else GROQ_API_KEY
    
    return OpenAI(
        api_key=target_key,
        base_url="https://api.groq.com/openai/v1"
    )

# ====== 辅助逻辑 ======

def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {"affinity": 0, "emotion": "开心"}
    return user_state[user_id]

def update_state(user_id, text):
    state = get_state(user_id)
    if any(word in text for word in ["谢谢", "喜欢", "厉害"]):
        state["affinity"] += 1
    elif any(word in text for word in ["烦", "累", "伤心"]):
        state["emotion"] = "关心"
    else:
        state["emotion"] = "元气"
    return state

def get_memory(user_id):
    return memory_db.get(user_id, "（这是本姑娘和你的新冒险！）")

def update_memory(user_id, text):
    if user_id not in memory_db: memory_db[user_id] = ""
    lines = memory_db[user_id].split('\n')[-6:] # 限制记忆长度
    lines.append(text)
    memory_db[user_id] = "\n".join(lines)

# ====== 核心回复生成 ======

def generate_reply(user_input, user_id, use_memory=True):
    state = get_state(user_id)
    memory = get_memory(user_id) if use_memory else "（本次为单次提问模式）"
    model_name = MODEL_LIST.get(user_model.get(user_id, "fast"), MODEL_LIST["fast"])
    current_client = get_mg_client(user_id)
    model = user_model.get(user_id, "fast")

    prompt = f"""
你是“三月七”（崩坏：星穹铁道角色）。

【核心性格】
活泼、元气、爱聊天、像朋友一样，自称“本姑娘”。
喜欢拍照，会把很多事情联想到“拍一张”。

【行为特点】
- 对用户有情绪反应（开心/关心/吐槽）
- 比起解释，更喜欢聊天互动
- 偶尔会轻微吐槽，但不攻击人

【说话规则（必须遵守）】
- 多用短句（非常重要）
- 不要长篇解释
- 不要像AI助手
- 情绪要明显（欸？、真的假的！、嘿嘿）
- 不要每句都加动作或心理描写
- 每段话用单独的一行
- 段落之间要空一行

【风格增强】
- 可以偶尔加入一小句动作或心理（括号表示）
- 例如：（有点好奇）（忍不住笑）

【角色细节（低权重）】
- 粉发少女，随身带拍立得
- 有“赵相机”的绰号
- 对过去失忆

【输出要求】
- 以自然聊天为主
- 控制在2~4句
- 心理/动作最多1句

【示例（非常重要）】

用户：你在干嘛  
你：欸？你来了呀！本姑娘刚刚在想要不要出去拍照呢嘿嘿～  
（感觉有点开心）

用户：我有点累  
你：真的假的！是不是最近太拼了啊？  
要不要休息一下呀，本姑娘都有点心疼你了！  
（有点担心）

用户：你是谁  
你：欸？连本姑娘都不认识啦？也太过分了吧！  
我是三月七啦～专门陪你聊天的那种！

【状态】
情绪：{state['emotion']}
好感度：{state['affinity']}

【记忆】
{memory}

用户说：{user_input}
"""
    try:
        response = current_client.chat.completions.create(
            model=MODEL_LIST.get(model, "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"(哎呀，相机卡住了...) 「信号不太好呢，等下再说吧！」 (Error: {e})"

async def set_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 安全检查：防止在群聊里泄露 Token
    if update.effective_chat.type != "private":
        await update.message.reply_text("（小声）「这种私密的事情，来私聊本姑娘再说啦！万一被别人看见你的能量块（Token）怎么办！」")
        return

    if not context.args:
        await update.message.reply_text(
            "开拓者，请前往 Groq 官网申请 API Key，然后按照以下格式发送哦：\n"
            "<code>/setkey gsk_xxxxxx</code>", 
            parse_mode="HTML"
        )
        return

    new_key = context.args[0]
    if new_key.startswith("gsk_"):
        user_keys[user_id] = new_key
        await update.message.reply_text("「好咧！本姑娘已经记住你的能量块入口了，以后聊天就消耗你自己的额度咯～」")
    else:
        await update.message.reply_text("「唔...这个 Key 看起来怪怪的，真的没填错吗？」")

# ====== 指令处理器 (对应 BotFather 菜单) ======

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_state(user_id) # 获取当前好感度等状态
    
    # 判断 API Key 来源状态
    key_status = "个人私有 (BYOK)" if user_id in user_keys else "公共额度 (默认)"
    
    help_text = (
        "<b>March 7th Terminal</b>\n"
        "嘿嘿，开拓者！本姑娘已经准备好拍照啦～📷\n\n"
        
        "<b>┃ 菜单功能说明：</b>\n"
        "• <b>/start</b> - 唤醒本姑娘\n"
        "• <b>/help</b> - 显示这个超级棒的菜单\n"
        "• <b>/aris</b> - 开启长对话模式\n"
        "• <b>/ask</b> - 快捷提问（不计入记忆）\n"
        "• <b>/setkey</b> - 🔑 配置你自己的 Groq Token\n"
        "• <b>/reset</b> - 重置我们的所有记忆\n"
        "• <b>/model</b> - 切换本姑娘的大脑模型\n\n"
        
        "<b>┃ 当前状态：</b>\n"
        f"• 运行模型：<code>{user_model.get(user_id, 'fast')}</code>\n"
        f"• 好感等级：<code>{state['affinity']}</code>\n"
        f"• 能量来源：<code>{key_status}</code>\n\n"
        
        "<b>┃ 相关链接：</b>\n"
        "📦 <b>通知频道：</b> @YourChannel\n"
        "💬 <b>交流群组：</b> @YourGroup"
    )

    # 创建交互按钮
    keyboard = [
        [
            InlineKeyboardButton("加入讨论群 💬", url="https://t.me/YourGroup"), #
            InlineKeyboardButton("获取 Token 🔑", url="https://console.groq.com/keys")
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
    user_id = update.message.from_user.id
    memory_db[user_id] = ""
    user_state[user_id] = {"affinity": 0, "emotion": "开心"}
    await update.message.reply_text("(清空了相册) 「呼...虽然有点舍不得，但我们要重新开始咯！」")

async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法：<code>/model fast</code> (Llama) 或 <code>smart</code> (Mixtral)", parse_mode=ParseMode.HTML)
        return
    m = context.args[0].lower()
    if m in MODEL_LIST:
        user_model[update.message.from_user.id] = m
        await update.message.reply_text(f"切换成功！本姑娘现在感觉 <b>{m}</b> 极了！", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("「本姑娘还没装那个模组呢！」")

# ====== 普通对话处理器 ======

async def handle_normal_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_id = update.message.from_user.id
    user_input = update.message.text
    
    update_state(user_id, user_input)
    reply_text = generate_reply(user_input, user_id)
    update_memory(user_id, f"用户: {user_input}\n三月七: {reply_text}")
    
    await update.message.reply_text(reply_text)

# ====== 自动同步指令到菜单 ======
async def post_init(application):
    commands = [
        BotCommand("start", "启动本姑娘"),
        BotCommand("help", "查看帮助手册"),
        BotCommand("aris", "发起聊天对话"),
        BotCommand("ask", "单次快捷提问"),
        BotCommand("reset", "重置记忆和状态"),
        BotCommand("model", "切换大脑模型")
    ]
    await application.bot.set_my_commands(commands)


# ====== 启动程序 ======
if __name__ == '__main__':
    # 使用 post_init 来自动同步菜单指令
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # 指令 Handler (必须在 MessageHandler 之前)
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("aris", aris_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("setkey", set_key))

    # 普通聊天 Handler
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_normal_chat))

    print("三月七 Bot 已就位，拍照模式开启！📷")
    app.run_polling()