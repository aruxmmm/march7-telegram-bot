# 更新日志 - v0.2 多 API 支持版本

发布时间：2026年4月6日

---

## 🎯 概述

v2.0 引入了 **Groq** 和 **Google Gemini** 双引擎支持，用户现在可以灵活选择和切换 AI 提供商，获得更好的性能和成本优化。

---

## ✨ 新增功能

### 1. 多 API 提供商支持
- 支持 Groq API（OpenAI 兼容接口）
- 支持 Google Gemini API（原生接口）
- 用户可同时配置两个 API 的 Key
- 用户可随时切换 API 提供商

### 2. 新命令：`/setapi`
**功能**：切换 AI 引擎
```
/setapi groq     # 切换到 Groq
/setapi gemini   # 切换到 Gemini
```

**特性**：
- 防止 API Key 泄露（仅在私聊中允许）
- 自动验证 Key 是否已配置
- 切换时自动重置模型为该 API 的默认型号

### 3. 扩展命令：`/setkey`
**旧用法**：
```
/setkey gsk_xxxxxx
```

**新用法**（向后兼容）：
```
/setkey groq gsk_xxxxxx   # 配置 Groq
/setkey gemini AI-xxxxxx  # 配置 Gemini
```

**特性**：
- 单个用户可配置多个 API 的 Key
- 两个 Key 独立存储和管理
- 增强的格式验证

### 4. 改进命令：`/model`
**支持的模型**：
```
• groq_fast     - Llama 3.3 70B (快速)
• groq_smart    - Mixtral 8x7B (智能)
• gemini_fast   - Gemini 1.5 Flash (快速)
• gemini_smart  - Gemini 1.5 Pro (智能)
```

**新特性**：
- 显示可用模型列表
- 支持 Groq 和 Gemini 模型混用
- 改进的用户提示

### 5. 增强命令：`/help`
显示额外信息：
- 当前 API 提供商
- 能量来源（个人 Key 还是公共额度）
- 配置的 API 列表（可点击获取 Key）

---

## 🏗️ 代码变化

### `config.py`
```python
# 新增
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 重构模型配置
MODEL_LIST = {
    "groq_fast": {"api": "groq", "model": "llama-3.3-70b-versatile"},
    "groq_smart": {"api": "groq", "model": "mixtral-8x7b-32768"},
    "gemini_fast": {"api": "gemini", "model": "gemini-2.5-flash"},
    "gemini_smart": {"api": "gemini", "model": "gemini-1.5-pro"},
}

# 向后兼容的映射
DEFAULT_MODELS = {
    "fast": "groq_fast",
    "smart": "groq_smart"
}

# 新增
user_keys = {}  # 现在支持多 API: {user_id: {"groq": "...", "gemini": "..."}}
user_api_provider = {}  # 用户当前选择的 API: {user_id: "groq"}
```

### `core/llm.py`
```python
# 新增
import google.generativeai as genai

# 重构客户端获取
def get_client(user_id, api_provider=None):
    """同时支持 Groq（OpenAI 兼容）和 Gemini（原生）"""
    
# 改进的生成函数
def generate_reply(user_input, user_id, use_memory=True):
    """自动选择 API 并调用"""
```

**核心逻辑**：
- 检测用户选择的 API 提供商
- 根据选择调用相应的 API 客户端
- 统一的错误处理

### `handlers/commands.py`
```python
# 新增
async def set_api(update, context):
    """切换 API 提供商"""

# 改进
async def set_key(update, context):
    """现在支持 /setkey groq|gemini <key>"""

# 改进
async def model_cmd(update, context):
    """显示可用模型列表"""
```

### `main.py`
```python
# 新增导入
from handlers.commands import set_api

# 新增 Handler
app.add_handler(CommandHandler("setapi", set_api))
```

### `requirements.txt`
```
新增：google-generativeai
```

---

## 📚 文档

### 新文件
| 文件 | 说明 |
|------|------|
| `API_SETUP.md` | 详细的 API 配置和使用指南 |
| `QUICKSTART.md` | 5 分钟快速开始指南 |
| `CHANGELOG.md` | 本文件 |

### 更新文件
| 文件 | 更新内容 |
|------|----------|
| `README.md` | 添加 API 切换命令说明和快速参考 |
| `test_imports.py` | 新增项目结构验证脚本 |

---

## 🔄 向后兼容性

所有现有功能都是向后兼容的！

### 旧代码迁移
```python
# ❌ 旧（仍然有效）
/setkey gsk_xxxxx
user_keys[123] = "gsk_xxxxx"

# ✅ 新（推荐）
/setkey groq gsk_xxxxx
user_keys[123] = {"groq": "gsk_xxxxx"}
```

### 自动检测
- 如果用户的 Key 是字符串格式（旧），系统自动识别为 Groq
- 自动转换为字典格式以支持多 API

---

## 🚀 性能对比

| 场景 | Groq | Gemini |
|------|------|--------|
| **聊天速度** | 🔥 极快 | ⚡ 快 |
| **模型强度** | 💪 不错 | 💪💪 更强 |
| **免费额度** | 30k/分钟 | 60 calls/分钟 |
| **成本** | 低 | 中 |
| **稳定性** | 高 | 高 |

**推荐**：日常聊天用 Groq，复杂任务用 Gemini。

---

## 🔐 安全改进

- `/setkey` 和 `/setapi` 仅在私聊中工作
- 防止 API Key 在公开群聊中泄露
- 改进的 Key 格式验证

---

## 🐛 已知问题与解决方案

### Google generativeai 库警告
```
FutureWarning: google.generativeai 包已停止维护
建议：切换到 google.genai（暂时还能用）
```

### 部分地区 Gemini API 不可用
解决方案：使用 Groq 作为主要 API

### 慢速初始化
首次导入 google.generativeai 可能需要几秒钟（正常现象）

---

## 📈 测试覆盖

✅ 所有模块导入成功（见 `test_imports.py`）
✅ 向后兼容性验证通过
✅ Groq API 集成测试
✅ Gemini API 集成测试
✅ 多 API 切换测试
✅ 错误处理测试

---

## 🎓 学习资源

- [快速开始](QUICKSTART.md)
- [API 配置详解](API_SETUP.md)
- [项目结构](README.md)

---

## 💬 反馈与贡献

如发现问题或有改进建议，欢迎：
- 报告 Bug
- 提出功能建议
- 分享使用经验

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.2 | 2026.04.06 | 🎉 多 API 支持、Gemini 集成 |
| v0.1 | 之前 | 初始版本（仅 Groq） |

---

**感谢使用 March7 机器人！** 🎉
