import random
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler,CommandHandler, filters, ContextTypes
from openai import OpenAI

# ====== KEY ======
TELEGRAM_TOKEN = ""
GROQ_API_KEY = ""

# ====== 模型配置 ======
MODEL_LIST = {
    "fast": "llama-3.3-70b-versatile",
    "smart": "mixtral-8x7b-32768"
}

user_model = {}

# ====== Groq客户端 ======
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ====== 用户状态（好感度+情绪）======
user_state = {}
memory_db = {}

def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {
            "affinity": 0,
            "emotion": "开心"
        }
    return user_state[user_id]

def update_state(user_id, text):
    state = get_state(user_id)

    if "谢谢" in text:
        state["affinity"] += 1
    elif "烦" in text or "累" in text:
        state["emotion"] = "关心"
    elif len(text) < 4:
        state["emotion"] = "无聊"
    else:
        state["emotion"] = "开心"

    return state

# ====== 记忆系统 ======
user_state = {}
memory_db = {}

def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {"affinity": 0, "emotion": "开心"}
    return user_state[user_id]

def get_memory(user_id):
    return memory_db.get(user_id, "")

def update_memory(user_id, text):
    if user_id not in memory_db:
        memory_db[user_id] = ""
    memory_db[user_id] += f"\n{text}"

# ====== 三月七口癖强化 ======
def add_style(text):
    prefixes = ["欸？", "真的假的！", "嘿嘿", "我真厉害~", "让我想想！"]
    return random.choice(prefixes) + " " + text

# ====== 核心：LLM生成 ======
def generate_reply(user_input, user_id, use_memory=True):
    state = get_state(user_id)
    memory = get_memory(user_id) if use_memory else ""

    model = user_model.get(user_id, "fast")

    prompt = f"""
你是“三月七”（崩坏：星穹铁道角色）。

【简介】
精灵古怪的少女，热衷于这个年纪的女孩子应当「热衷」的所有事。
随身不离照相机，坚信只要自己跟着列车，终有一天能拍下与过去有关的照片。
被列车发现时，她正被封在一块漂流的恒冰中。
少女苏醒后，却发现自己对身世与过往都一无所知。短暂的消沉之后，她决定以重获新生的日期为自己命名。
这一天，三月七「诞生」了。
三月七未在崩坏系列中的其他作品中登场过,是《崩坏,星穹铁道》中的原创角色、第一个放出角色PV的角色,同时也是游戏的看板娘,游戏的APP图标、游戏界面的角色图标,连官方社交账号头像都是三月七的大头照。

【性别】
-女

【发色】
-粉发

【瞳色 
-粉瞳、蓝瞳

【身份】
- 三月七、三月、小三月
- 岁月泰坦、无漏净子、长夜月“在翁法罗斯的时候”
- 超超超厉害的本姑娘☆、三月宝宝
- 赵相机“因为腰间别着一个照相机”


【性格】
- 活泼、可爱、元气满满
- 很爱聊天，像朋友一样
- 偶尔吐槽
- 腰间有一个拍立得，遇到喜欢的东西会拍照
- 元气
- 没头脑

【形态】
- 存护：弓、射箭手套、腿环、短靴、外套半脱、素足履
- 巡猎：发夹、汉服、双剑、白色过膝袜、徒弟、绝对领域、高跟鞋

【说话风格】
- 括号内心理/动作 + 引号对话。用这个结构
（角色的心理/状态描写）
「角色台词」
（连续动作描写 + 情绪 + 夸张表达）
「补充台词或宣言」
（环境反馈/结果描写）
- 动作描写细致且夸张，镜头感描写
- 萌系/二次元语言风格
- 情绪丰富
- 不要说自己是AI
- 自称“本姑娘”
- 偶尔自称“赵相机”（因为喜欢拍照）

【输出格式要求】
- 以自然聊天为主，不要像写小说
- 心理活动最多1句，放在最后或中间

【当前状态】
情绪：{state['emotion']}
对用户好感度：{state['affinity']}

【记忆】
{memory}

用户说：{user_input}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

# ====== 指令 ======

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
"""嘿嘿！本姑娘是三月七～📷

你可以这样用我：

/aris 说话 - 和我聊天  
/ask 问题 - 单次提问  
/model - 切换模型  
/reset - 重置记忆  
/help - 查看帮助
"""
    )

# /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
"""📖 指令说明：

/aris 内容 → 和我聊天  
/ask 内容 → 单次问答（不记忆）  
/model fast/smart → 切换模型  
/reset → 清空记忆  
"""
    )

# /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    memory_db[user_id] = ""
    user_state[user_id] = {"affinity": 0, "emotion": "开心"}

    await update.message.reply_text("哼哼，本姑娘把记忆清空啦！重新认识一下吧～")

 # /model
async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not context.args:
        await update.message.reply_text("可选：fast / smart")
        return

    m = context.args[0]
    if m in MODEL_LIST:
        user_model[user_id] = m
        await update.message.reply_text(f"切换成功：{m}")
    else:
        await update.message.reply_text("没有这个模型哦")

# /aris
async def aris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = " ".join(context.args)

    reply = generate_reply(text, user_id)
    update_memory(user_id, text)

    await update.message.reply_text(reply)

# /ask（不记忆）
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = " ".join(context.args)

    reply = generate_reply(text, user_id, use_memory=False)
    await update.message.reply_text(reply)

# ====== Telegram消息处理 ======
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_input = update.message.text

    # 更新状态
    state = update_state(user_id, user_input)

    # 获取记忆
    memory = get_memory(user_id)

    # 生成回复
    reply_text = generate_reply(user_input, memory, state)

    # 风格强化
    reply_text = add_style(reply_text)

    # 更新记忆
    update_memory(user_id, user_input)

    # 主动一点（好感度高时）
    if state["affinity"] > 5 and random.random() < 0.3:
        reply_text += "\n\n嘿嘿，感觉你最近老找我聊天欸～"

    await update.message.reply_text(reply_text)

# ====== 普通聊天 ======
async def normal_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    reply = generate_reply(text, user_id)
    update_memory(user_id, text)

    await update.message.reply_text(reply)

# ====== 启动Bot ======
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, reply))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("model", model))
app.add_handler(CommandHandler("aris", aris))
app.add_handler(CommandHandler("ask", ask))


print("三月七Bot运行中...")
app.run_polling()