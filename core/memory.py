# 对话记忆存储（由数据库管理）
from core.database import get_user_memory as db_get_user_memory
from core.database import append_user_memory as db_append_user_memory
from core.database import clear_user_memory as db_clear_user_memory
from core.state import get_prompt_name

# 保留这个字典用于向后兼容和缓存
memory_db = {}

def get_memory(user_id):
    """获取用户的对话记忆，优先从数据库读取"""
    try:
        prompt_name = get_prompt_name(user_id)
        try:
            return db_get_user_memory(user_id, prompt_name)
        except TypeError:
            # db_get_user_memory 仍保持向后兼容的旧签名
            return db_get_user_memory(user_id)
    except:
        # 降级到内存存储
        # 内存级别改为按 prompt 键保存：{(user_id, prompt): text}
        prompt_name = get_prompt_name(user_id)
        return memory_db.get((user_id, prompt_name), "（这是本姑娘和你的新冒险！）")

def update_memory(user_id, text):
    """更新用户的对话记忆"""
    try:
        prompt_name = get_prompt_name(user_id)
        db_append_user_memory(user_id, text, prompt_name)
    except TypeError:
        db_append_user_memory(user_id, text)
    except:
        # 降级到内存存储
        prompt_name = get_prompt_name(user_id)
        key = (user_id, prompt_name)
        if key not in memory_db:
            memory_db[key] = ""
        lines = memory_db[key].split('\n')[-6:]
        lines.append(text)
        memory_db[key] = "\n".join(lines)

def clear_memory(user_id, prompt_name=None):
    """清空用户的对话记忆。可选按 prompt 清空"""
    try:
        if prompt_name:
            try:
                db_clear_user_memory(user_id, prompt_name)
            except TypeError:
                db_clear_user_memory(user_id)
        else:
            db_clear_user_memory(user_id)
    except:
        # 降级到内存存储
        if prompt_name:
            key = (user_id, prompt_name)
            if key in memory_db:
                memory_db[key] = ""
        else:
            # 清空该用户所有 prompt 的内存记录
            keys = [k for k in list(memory_db.keys()) if isinstance(k, tuple) and k[0] == user_id]
            for k in keys:
                memory_db[k] = ""