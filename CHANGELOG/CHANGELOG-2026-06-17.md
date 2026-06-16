# 更新日志 - 2026-06-17

## 说明
记录 2026-06-17 对仓库所做的重要变更，便于回溯与发布说明。

## 变更概要

- 重命名并新增 Prompt：将 `changyeyue` 重命名为 `evernight`，新增文件 `prompt/evernight.py`，删除旧的 `prompt/changyeyue.py`。
- Prompt 切换改进：实现交互式 `/prompt` 菜单（按钮两列排列、当前角色高亮、预览与取消操作）。相关实现位于 `handlers/commands.py`（`build_prompt_menu`、`prompt_cmd`、回调处理）。
- 帮助文案美化：`/help` 输出改为更好看的 HTML 样式，并在状态中显示当前 Prompt（`handlers/help.py`）。
- 聊天记忆修复：修复 `core/memory.py` 中的 prompt 作用域读写逻辑，确保记忆按 `(user_id, prompt_name)` 保存并恢复。
- 聊天处理调整：`handlers/chat.py` 写入记忆时使用当前 prompt 名称（不再硬编码为“三月七”）。
- 主入口更新：`main.py` 中合并并注册了 prompt 回调，命令菜单更新为 `/prompt`（替代 `/showprompt`）。

## 影响文件（部分）

- `prompt/evernight.py` (新增)
- `handlers/commands.py` (prompt 菜单与回调)
- `handlers/help.py` (help 文案 + 当前 prompt 显示)
- `handlers/chat.py` (记忆写入改为使用当前 prompt)
- `core/memory.py` (prompt-aware memory get/update)
- `main.py` (命令注册更新)

## 建议的验证步骤

1. 启动 bot：`python main.py`（或用虚拟环境运行）。
2. 在 Telegram 中执行：`/prompt`，应弹出按钮菜单；点击可以切换为 `evernight`。
3. 发送消息并切换 prompt，确认记忆按不同 prompt 独立保存与恢复。

---

（自动生成）
