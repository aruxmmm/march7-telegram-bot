# 用户状态和模型选择存储（由数据库管理）
from core.database import get_user_state as db_get_user_state
from core.database import update_user_state as db_update_user_state
from core.database import get_user_model as db_get_user_model
from core.database import set_user_model as db_set_user_model
from core.database import get_user_prompt as db_get_user_prompt
from core.database import set_user_prompt as db_set_user_prompt

# 保留这些字典用于向后兼容和缓存
user_state = {}
user_model = {}

# Prompt 选择缓存（向后兼容）
user_prompt = {}

def get_prompt_name(user_id):
    """获取用户选择的 prompt 名称，优先从数据库读取"""
    try:
        return db_get_user_prompt(user_id)
    except:
        if user_id not in user_prompt:
            user_prompt[user_id] = 'march7'
        return user_prompt[user_id]


def set_prompt_name(user_id, prompt_name):
    """设置用户的 prompt 名称并持久化"""
    try:
        db_set_user_prompt(user_id, prompt_name)
    except:
        user_prompt[user_id] = prompt_name


def get_state(user_id):
    """获取用户状态，优先从数据库读取"""
    try:
        return db_get_user_state(user_id)
    except:
        # 降级到内存存储
        if user_id not in user_state:
            user_state[user_id] = {"affinity": 80, "emotion": "开心"}
        return user_state[user_id]

def update_state(user_id, text):
    """保留旧接口；状态变化由模型回复末尾的标记决定。"""
    return get_state(user_id)


def apply_model_state_update(user_id, affinity_delta, emotion, baseline=None):
    """验证模型建议的状态变化，再持久化保存。"""
    if not isinstance(affinity_delta, int) or not -10 <= affinity_delta <= 10:
        return get_state(user_id)

    state = dict(baseline) if baseline is not None else get_state(user_id)
    state["affinity"] = max(0, min(200, state["affinity"] + affinity_delta))
    emotion = str(emotion).strip()[:20]
    if emotion:
        state["emotion"] = emotion

    try:
        db_update_user_state(user_id, state["affinity"], state["emotion"])
    except:
        user_state[user_id] = state
    return state