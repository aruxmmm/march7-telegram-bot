# 用户状态和模型选择存储（由数据库管理）
from core.database import get_user_state as db_get_user_state
from core.database import update_user_state as db_update_user_state
from core.database import get_user_model as db_get_user_model
from core.database import set_user_model as db_set_user_model

# 保留这些字典用于向后兼容和缓存
user_state = {}
user_model = {}

def get_state(user_id):
    """获取用户状态，优先从数据库读取"""
    try:
        return db_get_user_state(user_id)
    except:
        # 降级到内存存储
        if user_id not in user_state:
            user_state[user_id] = {"affinity": 0, "emotion": "开心"}
        return user_state[user_id]

def update_state(user_id, text):
    """更新用户状态"""
    state = get_state(user_id)
    
    if any(word in text for word in ["谢谢", "喜欢", "厉害"]):
        state["affinity"] += 1
    elif any(word in text for word in ["烦", "累", "伤心"]):
        state["emotion"] = "关心"
    else:
        state["emotion"] = "元气"
    
    # 保存到数据库
    try:
        db_update_user_state(user_id, state["affinity"], state["emotion"])
    except:
        # 降级到内存存储
        user_state[user_id] = state
    
    return state