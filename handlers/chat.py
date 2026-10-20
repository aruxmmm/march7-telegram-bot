import asyncio
import logging
import mimetypes
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from core.state import get_prompt_name, get_state
from core.llm import generate_reply
from core.memory import replace_memory_entry, update_memory
from core.database import track_user_interaction

logger = logging.getLogger(__name__)
latest_chat_by_conversation = {}


async def _track_interaction(update):
    try:
        await asyncio.to_thread(track_user_interaction, update)
    except Exception:
        logger.exception("Failed to record user interaction")


async def _persist_memory(user_id, user_input, reply_text, image_data, is_sticker):
    try:
        current_prompt = await asyncio.to_thread(get_prompt_name, user_id)
        media_label = "贴纸" if is_sticker else "图片"
        memory_input = f"[{media_label}] {user_input}" if image_data else user_input
        memory_entry = f"用户: {memory_input}\n{current_prompt}: {reply_text}"
        await asyncio.to_thread(update_memory, user_id, memory_entry)
        return memory_entry
    except Exception:
        logger.exception("Failed to persist chat memory for user %s", user_id)
        return None


async def forget_latest_chats(user_id):
    keys = [
        key for key in latest_chat_by_conversation
        if key[1] == user_id
    ]
    pending_tasks = [
        latest_chat_by_conversation[key]["persist_task"]
        for key in keys
        if latest_chat_by_conversation[key]["persist_task"]
    ]
    for key in keys:
        latest_chat_by_conversation.pop(key, None)
    for task in pending_tasks:
        await task


async def handle_normal_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    context.application.create_task(_track_interaction(update), update=update)

    message = update.message
    image_data = None
    image_file_id = None
    image_mime_type = None
    if message.photo:
        image_file_id = message.photo[-1].file_id
        image_file = await context.bot.get_file(image_file_id)
        image_data = bytes(await image_file.download_as_bytearray())
        image_mime_type = "image/jpeg"
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        image_file_id = message.document.file_id
        image_file = await context.bot.get_file(image_file_id)
        image_data = bytes(await image_file.download_as_bytearray())
        image_mime_type = message.document.mime_type
    elif message.sticker:
        sticker = message.sticker
        if sticker.is_animated or sticker.is_video:
            if not sticker.thumbnail:
                await message.reply_text("这个是动态贴纸，本姑娘暂时看不了它的画面；发张截图给我看看嘛～")
                return
            image_file_id = sticker.thumbnail.file_id
            image_file = await context.bot.get_file(image_file_id)
            image_mime_type = mimetypes.guess_type(image_file.file_path or "")[0] or "image/jpeg"
        else:
            image_file_id = sticker.file_id
            image_file = await context.bot.get_file(image_file_id)
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

    state_baseline = dict(await asyncio.to_thread(get_state, user_id))
    reply_text = await asyncio.to_thread(
        generate_reply,
        user_input,
        user_id,
        image_data=image_data,
        image_mime_type=image_mime_type,
    )

    sent_message = await message.reply_text(reply_text)
    persist_task = context.application.create_task(
        _persist_memory(user_id, user_input, reply_text, image_data, bool(message.sticker)),
        update=update,
    )
    conversation_key = (update.effective_chat.id, user_id)
    latest_chat_by_conversation[conversation_key] = {
        "user_input": user_input,
        "image_file_id": image_file_id,
        "image_mime_type": image_mime_type,
        "is_sticker": bool(message.sticker),
        "reply_text": reply_text,
        "reply_message": sent_message,
        "persist_task": persist_task,
        "state_baseline": state_baseline,
    }


async def regenerate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    conversation_key = (update.effective_chat.id, user_id)
    latest_chat = latest_chat_by_conversation.get(conversation_key)
    if not latest_chat:
        await update.message.reply_text("「本次运行里还没有可重新生成的对话，先和本姑娘聊一句吧～」")
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    image_data = None
    if latest_chat["image_file_id"]:
        image_file = await context.bot.get_file(latest_chat["image_file_id"])
        image_data = bytes(await image_file.download_as_bytearray())

    persist_task = latest_chat["persist_task"]
    previous_entry = (
        await persist_task if persist_task else latest_chat["memory_entry"]
    )
    reply_text = await asyncio.to_thread(
        generate_reply,
        latest_chat["user_input"],
        user_id,
        image_data=image_data,
        image_mime_type=latest_chat["image_mime_type"],
        state_baseline=latest_chat["state_baseline"],
    )
    current_prompt = await asyncio.to_thread(get_prompt_name, user_id)
    media_label = "贴纸" if latest_chat["is_sticker"] else "图片"
    memory_input = (
        f"[{media_label}] {latest_chat['user_input']}"
        if latest_chat["image_file_id"]
        else latest_chat["user_input"]
    )
    new_entry = f"用户: {memory_input}\n{current_prompt}: {reply_text}"

    try:
        await latest_chat["reply_message"].edit_text(reply_text)
        sent_message = latest_chat["reply_message"]
    except BadRequest:
        logger.exception("Failed to edit regenerated reply; sending it as a new message")
        sent_message = await update.message.reply_text(reply_text)

    persisted_entry = previous_entry
    try:
        await asyncio.to_thread(
            replace_memory_entry,
            user_id,
            previous_entry,
            new_entry,
        )
        persisted_entry = new_entry
    except Exception:
        logger.exception("Failed to update regenerated chat memory for user %s", user_id)

    latest_chat_by_conversation[conversation_key] = {
        **latest_chat,
        "reply_text": reply_text,
        "reply_message": sent_message,
        "memory_entry": persisted_entry,
        "persist_task": None,
        "state_baseline": latest_chat["state_baseline"],
    }
