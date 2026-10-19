import os
import re
import sqlite3 as _sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USING_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

if USING_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row


class _PostgresCursor:
    """适配现有 SQLite 查询，使同一数据层可运行在 PostgreSQL 上。"""

    _PRIMARY_KEYS = {
        "user_api_keys": "user_id",
        "user_api_provider": "user_id",
        "user_state": "user_id",
        "user_model": "user_id",
        "user_prompt": "user_id",
        "user_memory_prompt": "user_id, prompt_name",
    }

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        sql = sql.replace("?", "%s")
        match = re.search(r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES", sql, re.I)
        if match:
            table, columns = match.groups()
            column_names = [column.strip() for column in columns.split(",")]
            primary_key = self._PRIMARY_KEYS[table]
            updates = ", ".join(
                f"{column} = EXCLUDED.{column}"
                for column in column_names
                if column not in {part.strip() for part in primary_key.split(",")}
            )
            sql = re.sub(r"INSERT\s+OR\s+REPLACE", "INSERT", sql, count=1, flags=re.I)
            sql += f" ON CONFLICT ({primary_key}) DO UPDATE SET {updates}"
        return self._cursor.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _PostgresConnection:
    def __init__(self):
        self._connection = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        self.row_factory = None  # 与 sqlite3.Connection 的调用方式兼容

    def cursor(self):
        return _PostgresCursor(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()


_sqlite_connect = _sqlite3.connect


def _connect(*args, **kwargs):
    if USING_POSTGRES:
        return _PostgresConnection()
    return _sqlite_connect(*args, **kwargs)


# 该模块的既有函数全部经由 sqlite3.connect 创建连接；仅在本模块中重定向。
sqlite3 = SimpleNamespace(
    connect=_connect,
    OperationalError=_sqlite3.OperationalError,
    Row=_sqlite3.Row,
)

# 数据库文件路径
# DB_PATH 允许部署环境把数据库放在持久化卷；相对路径仍以项目根目录为基准。
_configured_db_path = Path(os.getenv("DB_PATH", "march7_bot.db"))
DB_PATH = _configured_db_path if _configured_db_path.is_absolute() else Path(__file__).parent.parent / _configured_db_path

def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 用户 API Key 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_api_keys (
            user_id BIGINT PRIMARY KEY,
            groq_key TEXT,
            gemini_key TEXT,
            grok_key TEXT,
            agnes_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 数据库迁移：添加 grok_key 列（如果不存在）
    if not USING_POSTGRES:
        try:
            cursor.execute("ALTER TABLE user_api_keys ADD COLUMN grok_key TEXT")
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略错误
        try:
            cursor.execute("ALTER TABLE user_api_keys ADD COLUMN agnes_key TEXT")
        except sqlite3.OperationalError:
            pass  # 列已存在，忽略错误

        # 用户使用记录表（用于统计总使用人数）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
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
            user_id BIGINT PRIMARY KEY,
            provider TEXT DEFAULT 'groq',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户状态表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id BIGINT PRIMARY KEY,
            affinity INTEGER DEFAULT 80,
            emotion TEXT DEFAULT '开心',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户模型选择表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_model (
            user_id BIGINT PRIMARY KEY,
            model TEXT DEFAULT 'fast',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户对话记忆表（按 prompt 划分）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memory_prompt (
            user_id BIGINT,
            prompt_name TEXT DEFAULT 'march7',
            memory_text TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(user_id, prompt_name)
        )
    """)
    
    # 用户 Prompt 选择表（用于多 prompt 切换）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_prompt (
            user_id BIGINT PRIMARY KEY,
            prompt_name TEXT DEFAULT 'march7',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 将旧版本未初始化的好感度迁移到新的默认值；已累积的数值保持不变。
    cursor.execute("UPDATE user_state SET affinity = 80 WHERE affinity = 0")
    conn.commit()
    conn.close()
    print(f"✓ 数据库初始化成功: {DB_PATH}")

# ==================== API Keys 操作 ====================

def get_user_api_keys(user_id):
    """获取用户的 API Key"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT groq_key, gemini_key, grok_key, agnes_key FROM user_api_keys WHERE user_id = ?", (user_id,))
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
        if row['agnes_key']:
            keys['agnes'] = row['agnes_key']
        return keys
    return {}

def set_user_api_key(user_id, api_type, key):
    """设置用户的 API Key"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    api_type = api_type.lower()
    if api_type == 'groq':
        cursor.execute("""
            INSERT INTO user_api_keys (user_id, groq_key, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                groq_key = excluded.groq_key,
                updated_at = excluded.updated_at
        """, (user_id, key, datetime.now()))
    elif api_type == 'gemini':
        cursor.execute("""
            INSERT INTO user_api_keys (user_id, gemini_key, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                gemini_key = excluded.gemini_key,
                updated_at = excluded.updated_at
        """, (user_id, key, datetime.now()))
    elif api_type == 'grok':
        cursor.execute("""
            INSERT INTO user_api_keys (user_id, grok_key, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                grok_key = excluded.grok_key,
                updated_at = excluded.updated_at
        """, (user_id, key, datetime.now()))
    elif api_type == 'agnes':
        cursor.execute("""
            INSERT INTO user_api_keys (user_id, agnes_key, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                agnes_key = excluded.agnes_key,
                updated_at = excluded.updated_at
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
    
    return row['provider'] if row else 'agnes'

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
    
    # 重置为默认 API 提供商（agnes）
    cursor.execute("""
        INSERT OR REPLACE INTO user_api_provider (user_id, provider, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, 'agnes', datetime.now()))
    
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
    return {"affinity": 80, "emotion": "开心"}

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


def get_user_prompt(user_id):
    """获取用户选择的 prompt 名称，默认 'march7'"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT prompt_name FROM user_prompt WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    return row['prompt_name'] if row and row['prompt_name'] else 'march7'


def set_user_prompt(user_id, prompt_name):
    """设置用户的 prompt 名称"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO user_prompt (user_id, prompt_name, updated_at)
        VALUES (?, ?, ?)
    """, (user_id, prompt_name, datetime.now()))

    conn.commit()
    conn.close()

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

def get_user_memory_prompt(user_id, prompt_name='march7'):
    """获取用户的对话记忆，按 (user_id, prompt_name) 返回。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT memory_text FROM user_memory_prompt WHERE user_id = ? AND prompt_name = ?", (user_id, prompt_name))
    row = cursor.fetchone()
    conn.close()

    return row['memory_text'] if row and row['memory_text'] else "（这是本姑娘和你的新冒险！）"

def append_user_memory_prompt(user_id, text, prompt_name='march7'):
    """追加用户的对话记忆（按 prompt 存储，限制长度）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取现有记忆（针对指定 prompt）
    cursor.execute("SELECT memory_text FROM user_memory_prompt WHERE user_id = ? AND prompt_name = ?", (user_id, prompt_name))
    row = cursor.fetchone()
    current_memory = (row["memory_text"] if USING_POSTGRES else row[0]) if row else ""
    current_memory = current_memory or ""

    lines = current_memory.split('\n') if current_memory else []
    lines = lines[-6:]
    lines.append(text)
    new_memory = "\n".join(lines)

    cursor.execute("""
        INSERT OR REPLACE INTO user_memory_prompt (user_id, memory_text, prompt_name, updated_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, new_memory, prompt_name, datetime.now()))

    conn.commit()
    conn.close()

def clear_user_memory_prompt(user_id, prompt_name=None):
    """清空用户的对话记忆。
    - prompt_name=None: 清空该用户所有 prompt 的记忆（向后兼容）
    - prompt_name='name': 仅清空指定 prompt 的记忆
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if prompt_name:
        cursor.execute("""
            INSERT OR REPLACE INTO user_memory_prompt (user_id, memory_text, prompt_name, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, "", prompt_name, datetime.now()))
    else:
        # 清空所有记录（将每条 prompt 的 memory_text 设为空）
        cursor.execute("SELECT prompt_name FROM user_memory_prompt WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                pn = (r["prompt_name"] if USING_POSTGRES else r[0]) if r else 'march7'
                pn = pn or 'march7'
                cursor.execute("""
                    INSERT OR REPLACE INTO user_memory_prompt (user_id, memory_text, prompt_name, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, "", pn, datetime.now()))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO user_memory_prompt (user_id, memory_text, prompt_name, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, "", 'march7', datetime.now()))

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
            UNION SELECT user_id FROM user_memory_prompt
            UNION SELECT user_id FROM user_model
        )
    """)
    
    user_ids = [row["user_id"] if USING_POSTGRES else row[0] for row in cursor.fetchall()]
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
        "has_agnes_key": "agnes" in keys,
    }

def delete_user_data(user_id):
    """删除用户的所有数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_api_keys WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_api_provider WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_model WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_memory_prompt WHERE user_id = ?", (user_id,))
    
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
            total_interactions = users.total_interactions + 1
    """, (user_id, username, first_name))
    
    conn.commit()
    conn.close()

def get_total_users() -> int:
    """获取总使用人数（唯一用户数）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM users")
    row = cursor.fetchone()
    count = row["count"] if USING_POSTGRES else row[0]
    conn.close()
    return count

def get_active_users(days: int = 30) -> int:
    """获取最近 N 天活跃用户数"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS count FROM users
        WHERE last_interaction >= ?
    """, (datetime.now() - timedelta(days=days),))
    row = cursor.fetchone()
    count = row["count"] if USING_POSTGRES else row[0]
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

# 启动时自动初始化数据库并执行幂等迁移
init_db()


# 向后兼容的旧接口名（保持现有代码不变）
def get_user_memory(user_id, prompt_name='march7'):
    return get_user_memory_prompt(user_id, prompt_name)

def append_user_memory(user_id, text, prompt_name='march7'):
    return append_user_memory_prompt(user_id, text, prompt_name)

def clear_user_memory(user_id, prompt_name=None):
    return clear_user_memory_prompt(user_id, prompt_name)
