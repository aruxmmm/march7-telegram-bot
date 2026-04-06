from telegram import Update
from telegram.ext import ContextTypes
from core.state import update_state
from core.llm import generate_reply
from core.memory import update_memory

async def handle_normal_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.message.from_user.id
    user_input = update.message.text

    update_state(user_id, user_input)
    reply_text = generate_reply(user_input, user_id)
    update_memory(user_id, f"用户: {user_input}\n三月七: {reply_text}")

    await update.message.reply_text(reply_text)