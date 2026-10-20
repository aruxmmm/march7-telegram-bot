import asyncio
import logging
import os
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, MenuButtonCommands, Update
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, TypeHandler, filters
from config import TELEGRAM_TOKEN
from handlers.commands import start_cmd, ask_cmd, reset_cmd, memory_cmd, state_cmd, resetquota_cmd, model_cmd, model_callback, set_key, prompt_cmd
from handlers.help import help_cmd
from handlers.chat import handle_normal_chat, regenerate_cmd
from handlers.stats import stats_cmd

# 启动时初始化数据库和加载数据
try:
    from core.migration import migrate_data_to_db, load_data_from_db_to_memory
    print("初始化数据库...")
    migrate_data_to_db()
    load_data_from_db_to_memory()
except Exception as e:
    print(f"警告：数据库初始化失败: {e}")

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

COMMANDS = [
    BotCommand("start", "启动本姑娘"),
    BotCommand("help", "查看帮助手册"),
    BotCommand("ask", "单次快捷提问"),
    BotCommand("reset", "重置记忆和状态"),
    BotCommand("memory", "查看当前记忆"),
    BotCommand("regenerate", "重新生成上一条回复"),
    BotCommand("state", "查看当前好感度与情绪"),
    BotCommand("resetquota", "重置为公共额度"),
    BotCommand("model", "切换大脑模型"),
    BotCommand("prompt", "切换/查看/预览角色 prompt"),
    BotCommand("setkey", "配置 API Token"),
    BotCommand("stats", "查看统计数据"),
]

async def post_init(application):
    try:
        await _sync_bot_commands(application)
    except TelegramError:
        logger.exception("Could not sync Telegram commands during startup; the bot will still start")
        application.create_task(_retry_bot_command_sync(application), name="retry-bot-command-sync")


async def log_incoming_update(update, _context):
    message = update.effective_message
    text = message.text if message else None
    command = text.split(maxsplit=1)[0].split("@", 1)[0] if text and text.startswith("/") else None
    update_kind = "command" if command else "message" if message else "callback" if update.callback_query else "other"
    logger.info("Received Telegram update id=%s kind=%s command=%s", update.update_id, update_kind, command)


async def log_update_error(update, context):
    error = context.error
    logger.error(
        "Unhandled error while processing Telegram update id=%s",
        update.update_id if update else None,
        exc_info=(type(error), error, error.__traceback__) if error else None,
    )


async def log_completed_update(update, _context):
    logger.info("Finished processing Telegram update id=%s", update.update_id)


async def _sync_bot_commands(application):
    await application.bot.set_my_commands(COMMANDS)
    await application.bot.set_my_commands(COMMANDS, scope=BotCommandScopeAllPrivateChats())
    await application.bot.set_my_commands(COMMANDS, scope=BotCommandScopeAllGroupChats())
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def _retry_bot_command_sync(application):
    while True:
        await asyncio.sleep(5)
        if not application.running:
            return
        try:
            await _sync_bot_commands(application)
        except TelegramError:
            logger.exception("Could not sync Telegram commands; retrying in 5 seconds")
        else:
            logger.info("Telegram commands synced successfully")
            return


def main():
    if ":" not in TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_TOKEN 格式异常，Telegram Bot 未启动。")
        return

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .get_updates_connection_pool_size(2)
        .get_updates_pool_timeout(5)
        .post_init(post_init)
        .build()
    )

    # 指令 Handler (必须在 MessageHandler 之前)
    app.add_handler(TypeHandler(Update, log_incoming_update), group=-1)
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("memory", memory_cmd))
    app.add_handler(CommandHandler("regenerate", regenerate_cmd))
    app.add_handler(CommandHandler("state", state_cmd))
    app.add_handler(CommandHandler("resetquota", resetquota_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("prompt", prompt_cmd))
    app.add_handler(CallbackQueryHandler(model_callback, pattern=r"^(?:model_select:|model_api:|model_cancel|model_back|prompt_cancel|prompt_show|prompt_select:)") )
    app.add_handler(CommandHandler("setkey", set_key))
    app.add_handler(CommandHandler("stats", stats_cmd))

    # 普通聊天 Handler
    chat_filters = (filters.TEXT & (~filters.COMMAND)) | filters.PHOTO | filters.Document.IMAGE | filters.Sticker.ALL
    app.add_handler(MessageHandler(chat_filters, handle_normal_chat))
    app.add_handler(TypeHandler(Update, log_completed_update), group=99)
    app.add_error_handler(log_update_error)

    print("三月七 Bot 已就位，拍照模式开启！📷")
    webhook_url = os.environ.get("WEBHOOK_URL", "").rstrip("/")
    port = int(os.environ.get("PORT", 8080))
    if webhook_url:
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/{TELEGRAM_TOKEN}",
            url_path=TELEGRAM_TOKEN,
        )
    else:
        # 本地开发没有设置 WEBHOOK_URL 时回退到 polling
        app.run_polling()

if __name__ == '__main__':
    main()
