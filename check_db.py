#!/usr/bin/env python3
"""检查数据库结构"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "march7_bot.db"

if not DB_PATH.exists():
    print(f"✗ 数据库不存在: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 获取所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

print(f"✓ 数据库文件: {DB_PATH}")
print(f"✓ 共有 {len(tables)} 个表\n")

print("表结构:")
for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f"  📄 {table}")
    for col in columns:
        col_name, col_type = col[1], col[2]
        print(f"     ├─ {col_name} ({col_type})")
    
    # 显示记录数
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"     └─ 记录数: {count}\n")

conn.close()
print("✅ 数据库检查完成！")
