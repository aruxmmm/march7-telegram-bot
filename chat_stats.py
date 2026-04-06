#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话统计工具
显示有哪些用户和机器人互动，以及聊天内容
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

DB_PATH = Path(__file__).parent / "march7_bot.db"

def get_db_connection():
    """获取数据库连接"""
    if not DB_PATH.exists():
        print(f"✗ 数据库不存在: {DB_PATH}")
        return None
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_count():
    """获取用户总数"""
    conn = get_db_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id) as count FROM (
            SELECT user_id FROM user_api_keys
            UNION SELECT user_id FROM user_state
            UNION SELECT user_id FROM user_memory
            UNION SELECT user_id FROM user_model
        )
    """)
    count = cursor.fetchone()['count']
    conn.close()
    return count

def get_all_users():
    """获取所有用户 ID"""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT user_id FROM (
            SELECT user_id FROM user_api_keys
            UNION SELECT user_id FROM user_state
            UNION SELECT user_id FROM user_memory
            UNION SELECT user_id FROM user_model
        ) ORDER BY user_id
    """)
    users = [row['user_id'] for row in cursor.fetchall()]
    conn.close()
    return users

def get_user_info(user_id):
    """获取单个用户的完整信息"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    
    # 获取用户状态
    cursor.execute("SELECT affinity, emotion FROM user_state WHERE user_id = ?", (user_id,))
    state = cursor.fetchone()
    
    # 获取用户模型选择
    cursor.execute("SELECT model FROM user_model WHERE user_id = ?", (user_id,))
    model_row = cursor.fetchone()
    
    # 获取用户 API 配置
    cursor.execute("SELECT groq_key, gemini_key FROM user_api_keys WHERE user_id = ?", (user_id,))
    keys_row = cursor.fetchone()
    
    # 获取用户 API 选择
    cursor.execute("SELECT provider FROM user_api_provider WHERE user_id = ?", (user_id,))
    provider_row = cursor.fetchone()
    
    # 获取用户对话记忆
    cursor.execute("SELECT memory_text, updated_at FROM user_memory WHERE user_id = ?", (user_id,))
    memory_row = cursor.fetchone()
    
    # 获取创建时间（从最早的记录）
    cursor.execute("""
        SELECT MIN(created_at) as created_at FROM (
            SELECT created_at FROM user_state WHERE user_id = ?
            UNION ALL SELECT created_at FROM user_api_keys WHERE user_id = ?
            UNION ALL SELECT created_at FROM user_memory WHERE user_id = ?
        )
    """, (user_id, user_id, user_id))
    created_row = cursor.fetchone()
    
    conn.close()
    
    return {
        'user_id': user_id,
        'state': dict(state) if state else {'affinity': 0, 'emotion': '开心'},
        'model': model_row['model'] if model_row else 'fast',
        'provider': provider_row['provider'] if provider_row else 'groq',
        'has_groq_key': bool(keys_row and keys_row['groq_key']) if keys_row else False,
        'has_gemini_key': bool(keys_row and keys_row['gemini_key']) if keys_row else False,
        'memory': memory_row['memory_text'] if memory_row else '',
        'memory_updated': memory_row['updated_at'] if memory_row else None,
        'created_at': created_row['created_at'] if created_row and created_row['created_at'] else None,
    }

def print_summary():
    """打印统计摘要"""
    print("\n" + "="*60)
    print("📊 对话统计摘要")
    print("="*60)
    
    user_count = get_user_count()
    print(f"\n👥 用户统计:")
    print(f"   • 总用户数: {user_count}")
    
    # 统计配置了 Key 的用户
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM user_api_keys WHERE groq_key IS NOT NULL")
        groq_users = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM user_api_keys WHERE gemini_key IS NOT NULL")
        gemini_users = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM user_memory WHERE memory_text != ''")
        chat_users = cursor.fetchone()['count']
        
        conn.close()
        
        print(f"   • 配置 Groq Key: {groq_users} 个用户")
        print(f"   • 配置 Gemini Key: {gemini_users} 个用户")
        print(f"   • 有对话记录: {chat_users} 个用户")


def print_user_list():
    """打印用户列表"""
    users = get_all_users()
    
    if not users:
        print("\n⚠️  暂无用户数据")
        return
    
    print("\n" + "="*60)
    print("👥 用户列表")
    print("="*60)
    
    for i, user_id in enumerate(users, 1):
        info = get_user_info(user_id)
        print(f"\n{i}. 用户 ID: {user_id}")
        print(f"   • 好感度: {info['state']['affinity']}")
        print(f"   • 情绪: {info['state']['emotion']}")
        print(f"   • 模型: {info['model']}")
        print(f"   • API: {info['provider']}")
        
        apis_configured = []
        if info['has_groq_key']:
            apis_configured.append("Groq")
        if info['has_gemini_key']:
            apis_configured.append("Gemini")
        if apis_configured:
            print(f"   • 已配置: {', '.join(apis_configured)}")
        else:
            print(f"   • 已配置: 无（使用公共额度）")
        
        if info['memory']:
            print(f"   • 对话数: {len(info['memory'].split(chr(10)))}")
            print(f"   • 最后更新: {info['memory_updated']}")


def print_user_detailed(user_id):
    """打印用户详细信息"""
    info = get_user_info(user_id)
    
    if not info:
        print(f"✗ 用户 {user_id} 不存在")
        return
    
    print("\n" + "="*60)
    print(f"📋 用户 {user_id} 详细信息")
    print("="*60)
    
    print(f"\n基本信息:")
    print(f"   • 好感度: {info['state']['affinity']}")
    print(f"   • 情绪: {info['state']['emotion']}")
    print(f"   • 模型: {info['model']}")
    print(f"   • 当前 API: {info['provider']}")
    print(f"   • 创建时间: {info['created_at']}")
    
    print(f"\nAPI 配置:")
    print(f"   • Groq Key: {'✓ 已配置' if info['has_groq_key'] else '✗ 未配置'}")
    print(f"   • Gemini Key: {'✓ 已配置' if info['has_gemini_key'] else '✗ 未配置'}")
    
    if info['memory']:
        print(f"\n对话记忆 ({len(info['memory'].split(chr(10)))} 条):")
        print("-" * 60)
        
        # 显示最后 5 条对话
        lines = info['memory'].split('\n')
        display_lines = lines[-5:] if len(lines) > 5 else lines
        
        if len(lines) > 5:
            print(f"[... 共 {len(lines)} 条，显示最后 5 条 ...]\n")
        
        for line in display_lines:
            if line.strip():
                print(f"   {line}")
        
        print("-" * 60)
    else:
        print(f"\n📝 暂无对话记录")


def export_all_chats(filename='chat_export.txt'):
    """导出所有对话到文件"""
    users = get_all_users()
    
    if not users:
        print("⚠️  暂无用户数据")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"March7 Bot 对话导出\n")
        f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        for user_id in users:
            info = get_user_info(user_id)
            
            f.write(f"用户 ID: {user_id}\n")
            f.write(f"好感度: {info['state']['affinity']}\n")
            f.write(f"情绪: {info['state']['emotion']}\n")
            f.write(f"模型: {info['model']}\n")
            f.write(f"API: {info['provider']}\n")
            f.write(f"创建时间: {info['created_at']}\n")
            f.write("-"*60 + "\n")
            
            if info['memory']:
                f.write("对话记录:\n")
                f.write(info['memory'] + "\n")
            else:
                f.write("暂无对话记录\n")
            
            f.write("\n" + "="*60 + "\n\n")
    
    print(f"[完成] 已导出到 {filename}")


def interactive_mode():
    """交互模式"""
    print("\n" + "="*60)
    print("March7 Bot 对话统计工具")
    print("="*60)
    
    while True:
        print("\n请选择操作:")
        print("1. 查看统计摘要")
        print("2. 查看所有用户列表")
        print("3. 查看某个用户详情")
        print("4. 导出所有对话")
        print("0. 退出")
        
        choice = input("\n输入选择 (0-4): ").strip()
        
        if choice == "0":
            print("[退出] 再见！")
            break
        elif choice == "1":
            print_summary()
        elif choice == "2":
            print_user_list()
        elif choice == "3":
            try:
                user_id = int(input("输入用户 ID: "))
                print_user_detailed(user_id)
            except ValueError:
                print("[错误] 请输入正确的用户 ID")
        elif choice == "4":
            filename = input("输入导出文件名 (默认: chat_export.txt): ").strip()
            if not filename:
                filename = 'chat_export.txt'
            export_all_chats(filename)
        else:
            print("[错误] 无效的选择")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 命令行模式
        cmd = sys.argv[1]
        
        if cmd == "summary":
            print_summary()
        elif cmd == "list":
            print_user_list()
        elif cmd == "user" and len(sys.argv) > 2:
            try:
                user_id = int(sys.argv[2])
                print_user_detailed(user_id)
            except ValueError:
                print("✗ 请提供正确的用户 ID")
        elif cmd == "export":
            filename = sys.argv[2] if len(sys.argv) > 2 else 'chat_export.txt'
            export_all_chats(filename)
        else:
            print("用法:")
            print("  python chat_stats.py summary           # 查看统计摘要")
            print("  python chat_stats.py list              # 查看用户列表")
            print("  python chat_stats.py user <user_id>    # 查看用户详情")
            print("  python chat_stats.py export [filename] # 导出所有对话")
    else:
        # 交互模式
        interactive_mode()
