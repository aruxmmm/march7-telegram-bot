# 📷 March 7th Telegram Bot (三月七助手)

> “每一天都要留下新的记忆！嘿嘿，开拓者，快来和我合影吧～”

这是一个基于 Python 开发的 Telegram 机器人，可接入 **Agnes AI、Groq、Gemini、Grok 或本地 Ollama**。默认使用 Agnes 2.5 Flash，也支持自动发现本机 Ollama 模型。她不仅仅是一个 AI，还是那个活泼元气、爱吐槽、爱拍照的**三月七**！

---

## 📸 扫码以开始使用，或者点击下方tg小按钮

<img width="300" alt="march7_ai_bot_qrcode" src="https://github.com/user-attachments/assets/265ae68e-d3bc-4833-8556-746ffc6aac6d" />


[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/march7_ai_bot)

---

## ✨ 核心功能

- **元气对话**：深度还原三月七的人设，说话自带（心理/动作描写）。
- **动态记忆**：她能记住你最近说过的几句话，聊天不再“断片”。
- **多模型切换**：通过 `/model` 在云端模型和本地 Ollama 模型之间切换。
- **记忆查看**：通过 `/memory` 查看当前角色使用的对话记忆。

---

## 🛠️ 指令手册 (点击指令可直接触发)

在机器人对话框中，你可以使用以下“开拓者专用”指令：

| 指令 | 功能说明 |
| :--- | :--- |
| `/start` | 唤醒三月七，开始你们的冒险之旅！ |
| `/help` | 召唤详细的图形化功能菜单。 |
| `/ask` | 快捷提问。这种模式下不会占用大脑记忆。 |
| `/setkey` |  绑定自己的 Groq、Gemini 或 Grok Token。 |
| `/reset` | 格式化记忆。如果本姑娘坏掉了，用这个修理！ |
| `/memory` | 查看当前角色的对话记忆。 |
| `/resetquota` | 如果你的api额度满了，可以用这个重置为使用公共额度。|
| `/model` | 切换模型 |
| `/stats` | 查看统计数据。 |
| `/prompt` | 切换或预览角色 |

---

## 🚀 快速开始指南

如果你是第一次使用，请按照以下步骤操作：

1. **寻找机器人**：你可以使用[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/march7_ai_bot)，或者在 Telegram 搜索 `@march7_ai_bot` 并点击 `Start`。
2. **配置模型**：配置任意一个云端 API Key，或启动本地 Ollama。默认模型为 Agnes 2.5 Flash。
3. **绑定 Key（可选）**：私聊机器人发送 `/setkey groq gsk_你的Key`。
4. **开始聊天**：直接发消息，开始聊天吧！


<img width="579" height="760" alt="屏幕截图 2026-04-05 170816" src="https://github.com/user-attachments/assets/240c01b0-cd30-48db-b298-597761b25392" />
v0.1版本图
<img width="765" height="827" alt="image" src="https://github.com/user-attachments/assets/041ce035-c3a5-4fb0-aef9-8897b11d015c" />
v0.2版本图


---

## 📝 开发者说明 (如何自己部署)

如果你想架设属于自己的三月七 Bot，请参考以下步骤：

### 1. 克隆仓库
```bash
git clone https://github.com/aruxmmm/march7-telegram-bot.git
cd march7-telegram-bot
```

### 2. 安装依赖
确保你的电脑已安装 Python 3.10+，然后在终端运行：
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
在本地新建一个 `.env` 文件，或者在云端平台（如 Railway / HuggingFace）的设置页面添加以下变量：(LLM_API_KEY只需要任一即可运行)

| 变量名 | 获取渠道 | 说明 |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/Botfather) | 机器人的身份令牌 |
| `AGNES_API_KEY` | [Agnes AI](https://www.agnes-ai.com/) | Agnes AI API Key；默认模型为 `agnes-2.5-flash` |
| `AGNES_BASE_URL` | `https://apihub.agnes-ai.com/v1` | Agnes AI OpenAI 兼容接口地址（可选） |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) | Groq API Key |
| `GEMINI_API_KEY` | [Google AI Studio ](https://aistudio.google.com/) | Gemini API Key |
| `GROK_API_KEY` | [xAI Console](https://console.x.ai/) | Grok API Key |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434/v1` | Ollama 的 OpenAI 兼容地址 |
| `OLLAMA_MODEL` | 未设置 | 可选：指定一个额外的本地模型；未设置时自动读取 Ollama 已安装的全部模型 |
| `DB_PATH` | `march7_bot.db` | SQLite 数据库位置；相对路径以项目根目录为基准 |

Ollama 模型会在启动时以及执行 `/model` 时自动刷新。安装或删除模型无需修改源代码：
```bash
ollama pull qwen3.5:9b-mlx
ollama list
```

启动机器人后，使用 `/model` 选择 `Agnes AI` 或 `Ollama（本地）`。


### 4. 运行程序
```bash
python main.py
```

### 5. Docker 部署（推荐）
如果你想使用 Docker 部署，请确保已安装 Docker 和 Docker Compose。

#### 使用 Docker Compose（推荐）
1. 确保 `.env` 文件已配置（见步骤 3）。
2. 运行以下命令：
```bash
docker-compose up --build
```

#### 仅使用 Docker
```bash
# 构建镜像
docker build -t march7-bot .

# 运行容器（记得设置环境变量）
docker run -d --name march7-bot \
  -e TELEGRAM_TOKEN=your_token \
  -e AGNES_API_KEY=your_agnes_key \
  -e GROQ_API_KEY=your_key \
  -v $(pwd)/march7_bot.db:/app/march7_bot.db \
  march7-bot
```

> **aruxmmm的碎碎念**：
> “这个项目提供了bot的整体大框架，其实你自己就只用改一下prompt就可以开发属于自己的bot了。不过自己记得要新建token哦。”😘 
---

## 📅 更新日志
- **V0.1.0**: 2026/4/5 基础对话逻辑、好感度系统及上下文记忆功能上线。
- **V0.1.1**: 2026/4/6 将代码功能模块化拆分，增加了接入gemini-api的功能，修改了部分prompt，qqBOT功能测试中，小三月变得更聪明了。
- **V0.1.2**: 2026/4/8 修复了gemini旧版不兼容的问题，完成了v0.2中的数据库设计，小三月变得更聪明了。
- **V0.1.3**: 2026/4/21 增加了Grok-api，修改了部分代码结构，<del>不可以瑟瑟</del>。
- **V0.1.4**: 2026/4/28 更新了模型列表，修改了部分界面，铲除冗余代码-ing。
- **V0.1.5**: 2026/5/14 Docker化了仓库，增加了正在输入的显示，更新了部署服务器。
- **V0.2.0**: 2026/6/27 添加了角色切换功能，新添了长夜月，黑化强三倍，去试试新的prompt吧。
- **V0.2.1**: 2026/9/5 添加了免费的Agnes-api（杨教授，我们喜欢你），并作为默认模型，添加了调用ollma的选项，
- *更多功能正在开发中。...* 📷

---


<img width="300" alt="march7_ai_bot_qrcode" src="https://github.com/user-attachments/assets/265ae68e-d3bc-4833-8556-746ffc6aac6d" />

> **三月七的碎碎念**：
> “喂，那个叫 GitHub 的地方，记得给本姑娘点个 **Star** 哦！不然下次合照我就把你拍糊掉！” 📸

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/march7_ai_bot)

