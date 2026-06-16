from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from core.state import update_state
from core.llm import generate_reply
from core.memory import update_memory
from core.database import track_user_interaction

async def handle_normal_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user_interaction(update)
    if not update.message or not update.message.text:
        return
    user_id = update.message.from_user.id
    user_input = update.message.text

    # 发送正在输入的状态指示符
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    update_state(user_id, user_input)
    reply_text = generate_reply(user_input, user_id)
    from core.state import get_prompt_name
    current_prompt = get_prompt_name(user_id)
    update_memory(user_id, f"用户: {user_input}\n{current_prompt}: {reply_text}")

    await update.message.reply_text(reply_text)