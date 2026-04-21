import sqlite3
import json
from datetime import datetime
from pathlib import Path

# 数据库文件路径
DB_PATH = Path(__file__).parent.parent / "march7_bot.db"

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 用户 API Key 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_api_keys (
            user_id INTEGER PRIMARY KEY,
            groq_key TEXT,
            gemini_key TEXT,
            grok_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 数据库迁移：添加 grok_key 列（如果不存在）
    try:
        cursor.execute("ALTER TABLE user_api_keys ADD COLUMN grok_key TEXT")
    except sqlite3.OperationalError:
        pass  # 列已存在，忽略错误

        # 用户使用记录表（用于统计总使用人数）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_interactions INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 用户 API 提供商选择表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_api_provider (
            user_id INTEGER PRIMARY KEY,
            provider TEXT DEFAULT 'groq',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户状态表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            affinity INTEGER DEFAULT 0,
            emotion TEXT DEFAULT '开心',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户模型选择表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_model (
            user_id INTEGER PRIMARY KEY,
            model TEXT DEFAULT 'fast',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户对话记忆表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id INTEGER PRIMARY KEY,
            memory_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ 数据库初始化成功: {DB_PATH}")

# ==================== API Keys 操作 ====================

def get_user_api_keys(user_id):
    """获取用户的 API Key"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT groq_key, gemini_key, grok_key FROM user_api_keys WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        keys = {}
        if row['groq_key']:
            keys['groq'] = row['groq_key']
        if row['gemini_key']:
            keys['gemini'] = row['gemini_key']
        if row['grok_key']:
            keys['grok'] = row['grok_key']
        return keys
    return {}

def set_user_api_key(user_id, api_type, key):
    """设置用户的 API Key"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    api_type = api_type.lower()
    if api_type == 'groq':
        cursor.execute("""
            INSERT OR REPLACE INTO user_api_keys (user_id, groq_key, updated_at)
            VALUES (?, ?, ?)
        """, (user_id, key, datetime.now()))
    elif api_type == 'gemini':
        cursor.execute("""
            INSERT OR REPLACE INTO user_api_keys (user_id, gemini_key, updated_at)
            VALUES (?, ?, ?)
        """, (user_id, key, datetime.now()))
    elif api_type == 'grok':
        cursor.execute("""
            INSERT OR REPLACE INTO user_api_keys (user_id, grok_key, updated_at)
            VALUES (?, ?, ?)
        """, (user_id, key, datetime.now()))
    
    conn.commit()
    conn.close()

# ==================== API Provider 操作 ====================

def get_user_api_provider(user_id):
    """获取用户选择的 API 提供商"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT provider FROM user_api_provider WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row['provider'] if row else 'groq'

def set_user_api_provider(user_id, provider):
    """设置用户的 API 提供商"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_api_provider (user_id, provider, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, provider, datetime.now()))
    
    conn.commit()
    conn.close()

def clear_user_api_keys(user_id):
    """清除用户的所有 API Key（用于重置为公共额度）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM user_api_keys WHERE user_id = ?
    """, (user_id,))
    
    conn.commit()
    conn.close()

def reset_user_to_public_quota(user_id):
    """重置用户为使用公共额度（清除密钥并恢复默认 API 提供商）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清除所有 API Key
    cursor.execute("DELETE FROM user_api_keys WHERE user_id = ?", (user_id,))
    
    # 重置为默认 API 提供商（groq）
    cursor.execute("""
        INSERT OR REPLACE INTO user_api_provider (user_id, provider, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, 'groq', datetime.now()))
    
    conn.commit()
    conn.close()

# ==================== User State 操作 ====================

def get_user_state(user_id):
    """获取用户状态"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT affinity, emotion FROM user_state WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"affinity": row['affinity'], "emotion": row['emotion']}
    return {"affinity": 0, "emotion": "开心"}

def update_user_state(user_id, affinity=None, emotion=None):
    """更新用户状态"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_state = get_user_state(user_id)
    
    if affinity is None:
        affinity = current_state['affinity']
    if emotion is None:
        emotion = current_state['emotion']
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_state (user_id, affinity, emotion, updated_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, affinity, emotion, datetime.now()))
    
    conn.commit()
    conn.close()

# ==================== User Model 操作 ====================

def get_user_model(user_id):
    """获取用户选择的模型"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT model FROM user_model WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row['model'] if row else 'fast'

def set_user_model(user_id, model):
    """设置用户的模型"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_model (user_id, model, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, model, datetime.now()))
    
    conn.commit()
    conn.close()

# ==================== User Memory 操作 ====================

def get_user_memory(user_id):
    """获取用户的对话记忆"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT memory_text FROM user_memory WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row['memory_text'] if row and row['memory_text'] else "（这是本姑娘和你的新冒险！）"

def append_user_memory(user_id, text):
    """追加用户的对话记忆（限制长度）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取现有记忆
    current_memory = get_user_memory(user_id)
    
    # 如果是默认提示，则重置为空
    if current_memory == "（这是本姑娘和你的新冒险！）":
        current_memory = ""
    
    # 限制记忆行数（保留最近 6 条）
    lines = current_memory.split('\n') if current_memory else []
    lines = lines[-6:]  # 仅保留最后 6 行
    lines.append(text)
    new_memory = "\n".join(lines)
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_memory (user_id, memory_text, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, new_memory, datetime.now()))
    
    conn.commit()
    conn.close()

def clear_user_memory(user_id):
    """清空用户的对话记忆"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_memory (user_id, memory_text, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, "", datetime.now()))
    
    conn.commit()
    conn.close()

# ==================== 辅助函数 ====================

def load_all_users_from_db():
    """从数据库加载所有用户数据（用于启动时加载）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有用户 ID
    cursor.execute("""
        SELECT DISTINCT user_id FROM (
            SELECT user_id FROM user_api_keys
            UNION SELECT user_id FROM user_state
            UNION SELECT user_id FROM user_memory
            UNION SELECT user_id FROM user_model
        )
    """)
    
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return user_ids

def get_user_summary(user_id):
    """获取用户的完整信息摘要"""
    state = get_user_state(user_id)
    model = get_user_model(user_id)
    provider = get_user_api_provider(user_id)
    keys = get_user_api_keys(user_id)
    
    return {
        "user_id": user_id,
        "state": state,
        "model": model,
        "provider": provider,
        "has_groq_key": "groq" in keys,
        "has_gemini_key": "gemini" in keys,
    }

def delete_user_data(user_id):
    """删除用户的所有数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_api_keys WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_api_provider WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_model WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_memory WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()

# ==================== 用户使用统计 ====================

def track_user_interaction(update):
    """记录或更新用户互动（每次发消息/用命令时调用）"""
    if not update or not update.effective_user:
        return
    
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name or ""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_interaction, total_interactions)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
        ON CONFLICT(user_id) DO UPDATE SET 
            username = excluded.username,
            first_name = excluded.first_name,
            last_interaction = CURRENT_TIMESTAMP,
            total_interactions = total_interactions + 1
    """, (user_id, username, first_name))
    
    conn.commit()
    conn.close()

def get_total_users() -> int:
    """获取总使用人数（唯一用户数）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_users(days: int = 30) -> int:
    """获取最近 N 天活跃用户数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE last_interaction >= datetime('now', ?)
    """, (f'-{days} days',))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_interaction_stats(user_id: int):
    """获取单个用户的互动统计（可选）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT total_interactions, last_interaction FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"total_interactions": 0, "last_interaction": None}

# 启动时自动初始化数据库
if not DB_PATH.exists():
    init_db()
