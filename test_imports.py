#!/usr/bin/env python3
"""测试所有模块是否能正确导入"""

try:
    print("[1] 测试导入 config...")
    from config import GROQ_API_KEY, GEMINI_API_KEY, MODEL_LIST, user_keys, user_api_provider
    print(f"   ✓ GROQ_API_KEY: {bool(GROQ_API_KEY)}")
    print(f"   ✓ GEMINI_API_KEY: {bool(GEMINI_API_KEY)}")
    print(f"   ✓ 可用模型: {list(MODEL_LIST.keys())}")
    
    print("\n[2] 测试导入 core.llm...")
    from core.llm import get_client, generate_reply
    print("   ✓ get_client 和 generate_reply 导入成功")
    
    print("\n[3] 测试导入 core.state...")
    from core.state import get_state, user_model, user_state
    print("   ✓ 状态管理模块导入成功")
    
    print("\n[4] 测试导入 core.memory...")
    from core.memory import get_memory, update_memory, memory_db
    print("   ✓ 记忆管理模块导入成功")
    
    print("\n[5] 测试导入 handlers...")
    from handlers.commands import set_key, set_api, help_cmd, model_cmd
    print("   ✓ 命令处理模块导入成功")
    from handlers.chat import handle_normal_chat
    print("   ✓ 聊天处理模块导入成功")
    
    print("\n[6] 测试导入 prompt...")
    from prompt.march7 import get_prompt
    print("   ✓ 角色提示模块导入成功")
    
    print("\n✅ 所有模块导入成功！项目结构完整。")
    print("\n💡 下一步：")
    print("   1. 确保 .env 文件中配置了至少一个 API Key")
    print("   2. 运行: python main.py")
    
except Exception as e:
    print(f"\n❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
