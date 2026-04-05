<p align="center">
  <a href="#-中文版">中文版</a> | <a href="#-english-version">English Version</a>
</p>

---
# 📷 March 7th Telegram Bot (三月七助手)

> “每一天都要留下新的记忆！嘿嘿，开拓者，快来和我合影吧～”

这是一个基于 Python 开发的 Telegram 机器人，接入了 **Groq API** (Llama-3.3/Mixtral)。她不仅仅是一个 AI，还是那个活泼元气、爱吐槽、爱拍照的**三月七**！

---

## ✨ 核心功能

- **元气对话**：深度还原三月七的人设，说话自带（心理/动作描写）。
- **动态记忆**：她能记住你最近说过的几句话，聊天不再“断片”。
- **好感度系统**：你的言语会影响她的情绪和好感度，好感度高了有惊喜哦！
- **BYOK 模式**：支持“自带能源”，你可以填入自己的 Groq Token 运行，不消耗公共额度。
- **双模切换**：支持在极速模式 (Llama) 和逻辑模式 (Mixtral) 之间自由切换。

---

## 🛠️ 指令手册 (点击指令可直接触发)

在机器人对话框中，你可以使用以下“开拓者专用”指令：

| 指令 | 功能说明 |
| :--- | :--- |
| `/start` | 唤醒三月七，开始你们的冒险之旅！ |
| `/help` | 召唤详细的图形化功能菜单。 |
| `/setkey` | **[重要]** 绑定你自己的 Groq Token (建议私聊发送)。 |
| `/aris` | 开启长对话模式，本姑娘会一直陪你聊下去。 |
| `/model` | 切换大脑模型 (`fast` 极速 / `smart` 聪明)。 |
| `/reset` | 格式化记忆。如果本姑娘坏掉了，用这个修理！ |
| `/ask` | 快捷提问。这种模式下本姑娘不会占用大脑记忆。 |

---

## 🚀 快速开始指南

如果你是第一次使用，请按照以下步骤操作：

1. **寻找机器人**：开拓者，你可以使用最下面的连接，或者扫描二维码，或者在 Telegram 搜索 `@march7_ai_bot` 并点击 `Start`。
2. **配置能源 (可选)**：为了让本姑娘更有精神，建议去 [Groq Cloud](https://console.groq.com/keys) 免费申请一个 API Key。
3. **绑定 Key (可选)**：私聊机器人发送 `/setkey gsk_你的Key`。
4. **开始聊天**：直接发消息，或者用 `/aris` 调戏她吧！
<img width="579" height="760" alt="屏幕截图 2026-04-05 170816" src="https://github.com/user-attachments/assets/240c01b0-cd30-48db-b298-597761b25392" />

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
在本地新建一个 `.env` 文件，或者在云端平台（如 Railway / HuggingFace）的设置页面添加以下变量：

| 变量名 | 获取渠道 | 说明 |
| :--- | :--- | :--- |
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/Botfather) | 机器人的身份令牌 |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) | AI 大脑的能源 Key |

### 4. 运行程序
```bash
python main.py
```

---

## 📅 更新日志
- **V0.1**: 基础对话逻辑、好感度系统及上下文记忆功能上线。
- *更多功能（如发送表情包、好感度触发剧情）正在开发中...* 📷

---

## 📸 扫码开始冒险

<img width="300" alt="march7_ai_bot_qrcode" src="https://github.com/user-attachments/assets/265ae68e-d3bc-4833-8556-746ffc6aac6d" />

> **三月七的碎碎念**：
> “喂，那个叫 GitHub 的地方，记得给本姑娘点个 **Star** 哦！不然下次合照我就把你拍糊掉！” 📸

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/march7_ai_bot)

## 🇺🇸 English Version
---
# 📷 March 7th Telegram Bot (三月七助手)

> "Every day should leave a new memory! Hehe, Pioneer, come take a picture with me~"

This is a Telegram bot developed using Python and integrated with the **Groq API** (Llama-3.3/Mixtral). She's not just an AI, but also the lively, energetic, and photo-loving **March 7th**!

---

## ✨ Core Features

- **Energetic Conversation**: Deeply recreates March 7th's personality, with built-in descriptions of her thoughts and actions.

- **Dynamic Memory**: She can remember a few of your most recent conversations, eliminating "gap" in your chats.

- **Affection System**: Your words affect her mood and affection level; higher affection levels bring surprises!

- **BYOK Mode**: Supports "self-powered" operation. You can enter your own Groq Token to run it without consuming public quota.

- **Dual-Mode Switching**: Supports free switching between Llama and Mixtral modes.

---

## 🛠️ Command Manual (Click the command to trigger directly)

In the bot's chat box, you can use the following "Pioneer Exclusive" commands:

| Command | Function Description |

| :--- | :--- |

| `/start` | Awaken March 7th and begin your adventure! |

| `/help` | Summon the detailed graphical menu. |

| `/setkey` | **[Important]** Bind your own Groq Token (recommended to send via private message). |

| `/aris` | Enable long conversation mode; this girl will chat with you indefinitely. |

| `/model` | Switch brain model (`fast` Llama / `smart`). | | `/reset` | Format memory. If I break down, use this to fix it! |

| `/ask` | Ask a quick question. In this mode, I won't occupy my brain's memory. |

---

## 🚀 Quick Start Guide

If this is your first time using it, please follow these steps:

1. **Find the bot:** Pioneer, you can use the link at the bottom, scan the QR code, or search for `@march7_ai_bot` on Telegram and click `Start`.

2. **Configure power (optional):** To keep me energized, we recommend applying for a free API Key at [Groq Cloud](https://console.groq.com/keys).

3. **Bind Key (optional):** Send `/setkey gsk_yourKey` to the bot in a private message.

4. **Start chatting:** Send a message directly, or tease her with `/aris`!

<img width="579" height="760" alt="Screenshot 2026-04-05 170816" src="https://github.com/user-attachments/assets/240c01b0-cd30-48db-b298-597761b25392" />

---

## 📝 Developer Notes (How to Deploy Yourself)

If you want to set up your own March 7th Bot, please refer to the following steps:

### 1. Clone the Repository

```bash
git clone https://github.com/aruxmmm/march7-telegram-bot.git

cd march7-telegram-bot

```

### 2. Install Dependencies

Ensure your computer has Python 3.10+ installed, then run the following in the terminal:

```bash
pip install -r requirements.txt

```

### 3. Configure Environment Variables

Create a new `.env` file locally, or add the following variables in the settings page of a cloud platform (such as Railway/HuggingFace):

| Variable Name | Acquisition Channel | Description |

| :--- | :--- | :--- |

| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/Botfather) | Bot's Identity Token |

| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/keys) | AI Brain's Energy Key |

### 4. Run the Program

```bash
python main.py

```

---

## 📅 Update Log

- **V0.1**: Basic dialogue logic, affinity system, and context memory function are now online.

- *More features (such as sending emojis, triggering storylines based on affinity) are under development...* 📷

---

## 📸 Scan the code to start your adventure

<img width="300" alt="march7_ai_bot_qrcode" src="https://github.com/user-attachments/assets/265ae68e-d3bc-4833-8556-746ffc6aac6d" />

> **March 7th's Ramblings**:

> "Hey, that place called GitHub, remember to give me a **Star**! Otherwise, I'll blur you in the next photo!" 📸

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/march7_ai_bot)

