"""
数据库迁移工具
用于将现有内存中的数据迁移到 SQLite 数据库
"""

def migrate_data_to_db():
    """
    从内存数据结构迁移到数据库
    在机器人启动时调用此函数，将内存中的旧数据保存到数据库
    """
    try:
        from core.database import (
            set_user_api_key, set_user_api_provider, update_user_state,
            set_user_model, append_user_memory, get_user_memory
        )
        from config import user_keys, user_api_provider
        from core.state import user_state, user_model
        from core.memory import memory_db
    except ImportError:
        print("警告：数据库模块不可用，跳过迁移")
        return
    
    print("开始迁移数据到数据库...")
    
    migrated_users = set()
    
    # 迁移 API Key 和 Provider
    if user_keys:
        print(f"  迁移 {len(user_keys)} 个用户的 API Key...")
        for user_id, keys in user_keys.items():
            if isinstance(keys, dict):
                if 'groq' in keys:
                    set_user_api_key(user_id, 'groq', keys['groq'])
                if 'gemini' in keys:
                    set_user_api_key(user_id, 'gemini', keys['gemini'])
                if 'grok' in keys:
                    set_user_api_key(user_id, 'grok', keys['grok'])
            else:
                # 旧格式：字符串形式的 Groq Key
                set_user_api_key(user_id, 'groq', keys)
            migrated_users.add(user_id)
    
    # 迁移 API Provider
    if user_api_provider:
        print(f"  迁移 {len(user_api_provider)} 个用户的 API 选择...")
        for user_id, provider in user_api_provider.items():
            set_user_api_provider(user_id, provider)
            migrated_users.add(user_id)
    
    # 迁移 User State
    if user_state:
        print(f"  迁移 {len(user_state)} 个用户的状态...")
        for user_id, state in user_state.items():
            affinity = state.get('affinity', 0)
            emotion = state.get('emotion', '开心')
            update_user_state(user_id, affinity, emotion)
            migrated_users.add(user_id)
    
    # 迁移 User Model
    if user_model:
        print(f"  迁移 {len(user_model)} 个用户的模型选择...")
        for user_id, model in user_model.items():
            set_user_model(user_id, model)
            migrated_users.add(user_id)
    
    # 迁移 Memory
    if memory_db:
        print(f"  迁移 {len(memory_db)} 个用户的对话记忆...")
        for user_id, memory_text in memory_db.items():
            if memory_text and memory_text != "（这是本姑娘和你的新冒险！）":
                # 直接覆盖而不是追加
                try:
                    from core.database import DB_PATH
                    import sqlite3
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_memory (user_id, memory_text, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (user_id, memory_text))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"    警告：迁移用户 {user_id} 的记忆失败: {e}")
            migrated_users.add(user_id)
    
    print(f"✓ 数据迁移完成！共迁移 {len(migrated_users)} 个用户的数据")
    return migrated_users


def load_data_from_db_to_memory():
    """
    从数据库加载数据到内存（用于向后兼容）
    """
    try:
        from core.database import (
            get_user_api_keys, get_user_api_provider, get_user_state,
            get_user_model, get_user_memory, load_all_users_from_db
        )
        from config import user_keys, user_api_provider
        from core.state import user_state, user_model
        from core.memory import memory_db
    except ImportError:
        print("警告：数据库模块不可用，跳过加载")
        return
    
    print("从数据库加载用户数据到内存...")
    
    try:
        user_ids = load_all_users_from_db()
        
        for user_id in user_ids:
            # 加载 API Keys
            api_keys = get_user_api_keys(user_id)
            if api_keys:
                user_keys[user_id] = api_keys
            
            # 加载 API Provider
            provider = get_user_api_provider(user_id)
            if provider:
                user_api_provider[user_id] = provider
            
            # 加载 User State
            state = get_user_state(user_id)
            if state:
                user_state[user_id] = state
            
            # 加载 User Model
            model = get_user_model(user_id)
            if model:
                user_model[user_id] = model
            
            # 加载 Memory
            memory = get_user_memory(user_id)
            if memory and memory != "（这是本姑娘和你的新冒险！）":
                memory_db[user_id] = memory
        
        print(f"✓ 加载 {len(user_ids)} 个用户的数据到内存")
    except Exception as e:
        print(f"× 加载数据失败: {e}")


if __name__ == "__main__":
    print("数据库迁移工具")
    print("=" * 40)
    migrate_data_to_db()
    print("=" * 40)
    print("迁移完成！")
