import asyncio
import logging
import os
from telegram import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats, MenuButtonCommands, Update
from telegram.error import NetworkError, TelegramError
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, TypeHandler, filters
from telegram.request import HTTPXRequest
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
    # 启动连接自检：第一时间明确网络路径是否可用，避免静默失联
    try:
        me = await application.bot.get_me()
        logger.info("Telegram 连接自检通过: @%s", me.username)
    except TelegramError:
        proxy = os.environ.get("TELEGRAM_PROXY", "").strip()
        if proxy:
            logger.exception("无法连接 Telegram（代理 %s）。请检查代理是否运行且可用", proxy)
        else:
            logger.exception("无法连接 Telegram（直连路径，未设置 TELEGRAM_PROXY）。请检查网络（如 WARP），或设置 TELEGRAM_PROXY（例如 http://127.0.0.1:7890）走代理")
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
    if isinstance(error, NetworkError):
        # 网络层错误由 Updater 自动退避重试，只打一行警告，避免整屏堆栈刷屏
        logger.warning("Network error while polling (auto-retrying): %s", error)
    else:
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


def build_telegram_requests():
    """构建 bot 使用的两个请求实例（普通 API 请求 / get_updates 长轮询请求）。

    - 默认：强制直连（trust_env=False），忽略系统代理/环境变量代理，
      走操作系统默认路由（本机通常是 WARP TUN 透明代理），避免 httpx
      悄悄捡走系统代理（如 127.0.0.1:7890）导致长轮询随代理抖动断连。
    - 设置了 TELEGRAM_PROXY（如 http://127.0.0.1:7890）：显式使用该代理。
    """
    proxy = os.environ.get("TELEGRAM_PROXY", "").strip()
    if proxy:
        logger.info("Telegram 网络路径: 显式代理 %s", proxy)
        request = HTTPXRequest(proxy=proxy)
        get_updates_request = HTTPXRequest(proxy=proxy, connection_pool_size=2, pool_timeout=5)
    else:
        logger.info("Telegram 网络路径: 直连（已忽略系统/环境变量代理，未设置 TELEGRAM_PROXY）")
        request = HTTPXRequest(httpx_kwargs={"trust_env": False})
        get_updates_request = HTTPXRequest(
            httpx_kwargs={"trust_env": False},
            connection_pool_size=2,
            pool_timeout=5,
        )
    return request, get_updates_request


def main():
    if ":" not in TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_TOKEN 格式异常，Telegram Bot 未启动。")
        return

    request, get_updates_request = build_telegram_requests()
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
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
