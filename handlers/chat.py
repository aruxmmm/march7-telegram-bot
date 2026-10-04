import mimetypes
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from core.state import update_state
from core.llm import generate_reply
from core.memory import update_memory
from core.database import track_user_interaction

async def handle_normal_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user_interaction(update)
    if not update.message:
        return

    message = update.message
    image_data = None
    image_mime_type = None
    if message.photo:
        image_file = await context.bot.get_file(message.photo[-1].file_id)
        image_data = bytes(await image_file.download_as_bytearray())
        image_mime_type = "image/jpeg"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        image_file = await context.bot.get_file(message.document.file_id)
        image_data = bytes(await image_file.download_as_bytearray())
        image_mime_type = message.document.mime_type
    elif message.sticker:
        sticker = message.sticker
        if sticker.is_animated or sticker.is_video:
            if not sticker.thumbnail:
                await message.reply_text("这个是动态贴纸，本姑娘暂时看不了它的画面；发张截图给我看看嘛～")
                return
            image_file = await context.bot.get_file(sticker.thumbnail.file_id)
            image_mime_type = mimetypes.guess_type(image_file.file_path or "")[0] or "image/jpeg"
        else:
            image_file = await context.bot.get_file(sticker.file_id)
            image_mime_type = "image/webp"
        image_data = bytes(await image_file.download_as_bytearray())

    if not message.text and not image_data:
        return

    user_id = update.message.from_user.id
    user_input = message.text or message.caption or (
        "用户发来一个贴纸，请结合图案自然回应。" if message.sticker else "请描述这张图片。"
    )

    # 发送正在输入的状态指示符
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    update_state(user_id, user_input)
    reply_text = generate_reply(
        user_input,
        user_id,
        image_data=image_data,
        image_mime_type=image_mime_type,
    )
    from core.state import get_prompt_name
    current_prompt = get_prompt_name(user_id)
    media_label = "贴纸" if message.sticker else "图片"
    memory_input = f"[{media_label}] {user_input}" if image_data else user_input
    update_memory(user_id, f"用户: {memory_input}\n{current_prompt}: {reply_text}")

    await message.reply_text(reply_text)