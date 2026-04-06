# 对话记忆存储（由数据库管理）
from core.database import get_user_memory as db_get_user_memory
from core.database import append_user_memory as db_append_user_memory
from core.database import clear_user_memory as db_clear_user_memory

# 保留这个字典用于向后兼容和缓存
memory_db = {}

def get_memory(user_id):
    """获取用户的对话记忆，优先从数据库读取"""
    try:
        return db_get_user_memory(user_id)
    except:
        # 降级到内存存储
        return memory_db.get(user_id, "（这是本姑娘和你的新冒险！）")

def update_memory(user_id, text):
    """更新用户的对话记忆"""
    try:
        db_append_user_memory(user_id, text)
    except:
        # 降级到内存存储
        if user_id not in memory_db:
            memory_db[user_id] = ""
        lines = memory_db[user_id].split('\n')[-6:]  # 限制记忆长度
        lines.append(text)
        memory_db[user_id] = "\n".join(lines)

def clear_memory(user_id):
    """清空用户的对话记忆"""
    try:
        db_clear_user_memory(user_id)
    except:
        # 降级到内存存储
        if user_id in memory_db:
            memory_db[user_id] = ""