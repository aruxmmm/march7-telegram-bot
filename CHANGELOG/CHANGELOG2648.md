核心改动在于：**剔除了已报废的旧版 SDK，全面转向 `google-genai` 架构，并更新了 2026 年最新的模型配额逻辑。**

---

# 更新日志 - v0.2.2 驱动重构版

**发布时间**：2026年4月7日
**核心状态**：✅ 稳定版 (Stable)

---

## 🎯 概述

v0.2.2 是一个重大的技术重构版本。由于 `google-generativeai` 旧版 SDK 在 Python 3.13 环境下出现认证失效及 404 路径错误，本项目已全面切换至 **Google GenAI 统一架构**，并优化了 Gemini 2.5 时代的模型适配。

---

## ✨ 新增与优化功能

### 1. 引擎驱动升级 (Breaking Changes)
- **SDK 迁移**：从 `google-generativeai` 迁移至官方最新的 **`google-genai`**。
- **架构重构**：由“全局配置模式”改为“客户端实例模式”，彻底解决多用户并发时 API Key 混淆的 Bug。
- **环境适配**：完美适配 **Python 3.13**，修复了旧版 SDK 在新版 Python 下的 Stub 报错。

### 2. 模型库更新
**支持的模型**（根据 2026.04 实际配额调整）：
```text
• groq_fast    - Llama 3.3 70B (极速)
• groq_smart   - Mixtral 8x7B (逻辑强)
• gemini_fast  - Gemini 2.5 Flash (推荐：当前免费层级主力)
• gemini_smart - Gemini 2.5 Pro (全能：需确认配额)
• gemini_next  - Gemini 3.1 Flash-Lite (实验性预览版)
```

### 3. 命令系统增强
- **`/setapi`**：切换逻辑优化，切换到 Gemini 时会自动实例化对应的 GenAI 客户端。
- **`/model`**：现在会根据当前 API 提供商动态过滤掉不可用的模型选项。
- **`/setkey`**：增强了对新版 Gemini Key 的格式校验。

---

## 🏗️ 核心代码变化

### `core/llm.py` (关键重构)
```python
# ✅ 旧版导入已移除：import google.generativeai as genai
# ✅ 新版导入：
from google import genai 

def get_client(user_id, api_provider=None):
    """
    不再返回字符串，而是直接返回 Client 实例。
    Gemini 实例化方式：genai.Client(api_key=target_key)
    """

def generate_reply(user_input, user_id, use_memory=True):
    """
    1. 修正了 api_provider 的赋值顺序，防止 UnboundLocalError。
    2. 使用 client.models.generate_content(model=model_name, contents=prompt) 调用。
    """
```

### `config.py`
```python
# 更新模型映射：Gemini 1.5/2.0 在免费层级可能报 404 或 429(Limit 0)
MODEL_LIST = {
    "gemini_fast": {"api": "gemini", "model": "gemini-2.5-flash"},
    "gemini_smart": {"api": "gemini", "model": "gemini-2.5-pro"},
}
```

### `requirements.txt`
```text
# ❌ 移除旧版：google-generativeai
# ✅ 替换为：google-genai
```

---

## 🔄 向后兼容性与迁移

### 自动字典化
如果你之前的 `user_keys` 存储的是字符串（旧版 Groq 格式），系统在初始化时会自动将其转换为 `{"groq": "old_key"}` 格式，确保无感升级。

### 接口映射
旧版的 `/setkey AIza...` 会被智能识别为 Gemini Key 并归类。

---

## 🚀 性能与配额参考 (2026.04)

| 场景 | Groq | Gemini (New SDK) |
|------|------|--------|
| **首字延迟** | ⚡ 毫秒级 | 🚄 秒级 |
| **上下文长度** | 128k | **2M+ (极强)** |
| **免费配额** | 稳定 | 波动（建议绑定卡以激活 2.5 配额） |
| **多模态** | 仅文本 | **支持图片/视频/语音分析** |

---

## 🐞 已修复的问题

1. **404 Models Not Found**: 修复了旧 SDK 强制请求 `v1beta` 路径导致无法识别新模型的问题。
2. **DefaultCredentialsError**: 修复了 Pylance/Python 3.13 环境下找不到 API Key 的认证 Bug。
3. **UnboundLocalError**: 修复了变量在赋值前被引用的逻辑漏洞。

---

## 📸 三月七的寄语
“嘿嘿，本姑娘的‘相机’终于换上最先进的 **2.5 闪现镜头** 啦！不仅拍得更清楚，快门也更稳了哦。开拓者，快去 Telegram 里试试新功能吧，千万别被本姑娘的智慧惊呆了呢！✨”

---

**March7 Bot Project** *Live with passion, Capture with heart.* 📸