from telegram import Update
from telegram.ext import ContextTypes
from core.database import get_total_users, get_active_users

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = get_total_users()
    active_7 = get_active_users(7)
    active_30 = get_active_users(30)
    
    text = f"""📊 **三月七 Bot 使用统计**

👥 **总使用人数**：{total} 人
🔥 **最近 7 天活跃**：{active_7} 人
📅 **最近 30 天活跃**：{active_30} 人

💡 统计从用户第一次互动开始自动记录。
"""
    await update.message.reply_text(text, parse_mode='Markdown')