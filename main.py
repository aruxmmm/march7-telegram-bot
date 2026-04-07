import logging
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
from config import TELEGRAM_TOKEN, QQ_BOT_ENABLED
from handlers.commands import start_cmd, help_cmd, aris_cmd, ask_cmd, reset_cmd, model_cmd, set_key, set_api
from handlers.chat import handle_normal_chat
from handlers.stats import stats_cmd

if QQ_BOT_ENABLED:
    from qq_main import start_qq_bot

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

async def post_init(application):
    commands = [
        BotCommand("start", "启动本姑娘"),
        BotCommand("help", "查看帮助手册"),
        BotCommand("aris", "发起聊天对话"),
        BotCommand("ask", "单次快捷提问"),
        BotCommand("reset", "重置记忆和状态"),
        BotCommand("model", "切换大脑模型"),
        BotCommand("setkey", "配置 API Token"),
        BotCommand("setapi", "切换 API 提供商"),
        BotCommand("stats", "查看统计数据")
        
    ]
    await application.bot.set_my_commands(commands)

def main():
    app = None

    if TELEGRAM_TOKEN and ":" in TELEGRAM_TOKEN:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

        # 指令 Handler (必须在 MessageHandler 之前)
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("aris", aris_cmd))
        app.add_handler(CommandHandler("ask", ask_cmd))
        app.add_handler(CommandHandler("reset", reset_cmd))
        app.add_handler(CommandHandler("model", model_cmd))
        app.add_handler(CommandHandler("setkey", set_key))
        app.add_handler(CommandHandler("setapi", set_api))
        app.add_handler(CommandHandler("stats", stats_cmd))

        # 普通聊天 Handler
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_normal_chat))

    elif TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_TOKEN 存在但格式异常，Telegram Bot 未启动。")

    if QQ_BOT_ENABLED:
        start_qq_bot(block=False)
        print("QQ Bot 已就绪，正在监听 OneBot 事件。")

    if app:
        print("三月七 Bot 已就位，拍照模式开启！📷")
        app.run_polling()
    elif QQ_BOT_ENABLED:
        print("仅 QQ Bot 已启动，请保持程序运行。按 Ctrl+C 退出。")
        try:
            import time
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            print("QQ Bot 停止。")
    else:
        logger.error("没有可用的 Bot 入口，程序退出。")

if __name__ == '__main__':
    main()
