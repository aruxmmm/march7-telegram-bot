# QQ 接入傻瓜指南

本指南将一步步教你如何将一个QQ号变成机器人号，并接入到三月七Telegram机器人项目中。跟着步骤做，即使是小白也能轻松完成！

## 准备工作

### 需要的软件和下载链接

1. **Python 3.8+** （如果还没安装）
   - 下载链接：https://www.python.org/downloads/
   - 安装时记得勾选 "Add Python to PATH"

2. **QQ客户端** （推荐使用轻聊版，避免被封号）
   - 下载链接：https://im.qq.com/lightqq/
   - 或者使用官方QQ：https://im.qq.com/

3. **go-cqhttp** （OneBot框架，用于QQ机器人）
   - 下载链接：https://github.com/Mrs4s/go-cqhttp/releases
   - 下载最新版本的 `go-cqhttp_windows_amd64.exe` 或 `go-cqhttp_windows_386.exe` （根据你的系统选择）

4. **项目依赖** （requirements.txt已包含）
   - 无需单独下载，后面会安装

### 其他要求
- 一个可用的QQ号（建议用小号，避免主号被封）
- 稳定的网络连接

## 步骤1：安装Python和依赖

1. 下载并安装Python（见上面的链接）。
2. 打开命令提示符（Win+R，输入cmd，回车）。
3. 进入项目目录：
   ```
   cd C:\Users\12734\Desktop\2\march7-telegram-bot
   ```
4. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

## 步骤2：下载和配置go-cqhttp

1. 下载go-cqhttp（见上面的链接），解压到项目目录下的 `qq_bot` 文件夹。
   - 如果没有 `qq_bot` 文件夹，先创建：`mkdir qq_bot`
   - 将 `go-cqhttp.exe` 放到 `qq_bot` 文件夹里。

2. 在 `qq_bot` 文件夹中创建一个配置文件 `config.yml`：
   ```yaml
   # go-cqhttp 默认配置文件

   account: # 账号相关
     uin: 你的QQ号 # QQ账号
     password: '' # 为空表示使用扫码登录
     encrypt: false
     status: 0
     relogin:
       delay: 3
       interval: 3
       max-times: 0
     use-sso-address: true
     allow-temp-session: false

   database: # 数据库相关
     leveldb:
       enable: true

   servers: # 服务器相关
     - http: # HTTP API 插件
         address: 0.0.0.0:5700 # 监听地址
         version: 11 # OneBot版本, 推荐 11
         timeout: 5 # 反向 HTTP 超时时间, 单位秒
         long-polling: # 长轮询拓展
           enabled: false
           max-queue-size: 2000
         middlewares:
           <<: *default # 引用默认中间件
         post: # 事件推送
           - url: http://127.0.0.1:8080/ # 推送地址
             secret: '' # 密钥
             max-retries: 3 # 最大重试, 0 时不重试
             retries-interval: 1500 # 重试间隔, 单位毫秒

   ```

   注意：将 `你的QQ号` 替换为实际值。`password` 留空时，go-cqhttp 启动时会进入扫码登录流程。

## 步骤3：将QQ号变成机器人号

1. **安装QQ客户端**：
   - 下载并安装QQ轻聊版（见上面的链接）。

2. **登录QQ号**：
   - 打开QQ客户端，登录你要变成机器人的QQ号。
   - 确保这个QQ号没有开启设备锁或安全验证（如果有，需要关闭）。

3. **启动go-cqhttp**：
   - 打开命令提示符，进入 `qq_bot` 文件夹：
     ```
     cd C:\Users\12734\Desktop\2\march7-telegram-bot\qq_bot
     ```
   - 运行go-cqhttp：
     ```
     go-cqhttp.exe
     ```
   - 如果是第一次运行，它会生成配置文件并输出登录提示。按提示操作。
   - 如果 `config.yml` 中 `password` 为空，go-cqhttp 会进入扫码登录模式：
     - 在终端或程序界面显示二维码
     - 使用你的 QQ 手机/客户端扫码登录
   - 登录成功后，`go-cqhttp` 会保存登录会话到 `qq_bot/data/` 或 `qq_bot/device.json`，后续可直接复用，不必每次扫码。
   - 如果需要重新登录，删除 `qq_bot/data/` 或 `qq_bot/device.json` 后重新启动。

4. **验证机器人上线**：
   - 在QQ中，给这个机器人QQ号发消息，应该能收到回复（如果项目已启动）。
   - 机器人现在已经在线，可以接收和发送消息。

## 步骤4：配置项目环境

1. 在项目根目录创建 `.env` 文件（如果没有）：
   ```
   QQ_BOT_ENABLED=true
   QQ_BOT_API_URL=http://127.0.0.1:5700
   QQ_BOT_PORT=8080
   QQ_BOT_SECRET=  # 如果go-cqhttp配置了secret，就填这里

   # QQ账号信息（用于go-cqhttp环境变量替换）
   QQ_UIN=你的QQ号
   QQ_PASSWORD=你的QQ密码

   # AI Key，至少填一个
   GROQ_API_KEY=你的GROQ_API_KEY
   GEMINI_API_KEY=你的GEMINI_API_KEY
   ```

   - `QQ_UIN` 和 `QQ_PASSWORD` 用于替换config.yml中的占位符，避免明文存储敏感信息。
   - `GROQ_API_KEY` 和 `GEMINI_API_KEY` 需要去相应网站申请。

## 步骤5：启动机器人

1. 确保go-cqhttp已经启动并登录QQ。
2. 打开另一个命令提示符，进入项目目录：
   ```
   cd C:\Users\12734\Desktop\2\march7-telegram-bot
   ```
3. 启动QQ机器人：
   ```
   python qq_main.py
   ```
4. 查看日志，确保看到 "QQ Bot 已就绪，正在监听 OneBot 事件。" 或类似成功信息。

## 步骤6：测试机器人

1. 用另一个QQ号添加机器人QQ为好友。
2. 发送消息测试，例如："你好" 或 "/help"。
3. 如果机器人回复正常，恭喜你成功了！

## 常见问题

- **登录失败**：检查QQ号密码是否正确，尝试扫码登录。
- **网络问题**：确保防火墙允许go-cqhttp访问网络。
- **消息不回复**：检查.env配置和端口是否正确。
- **被封号**：QQ机器人有风险，建议用小号。

## 进阶使用

- **群聊**：将机器人QQ拉进群，@它或用命令前缀触发。
- **同时运行Telegram和QQ**：运行 `python main.py` 而不是 `qq_main.py`。

如果遇到问题，请查看项目日志或寻求帮助！

## 6. 常用命令

私聊和群聊中均支持以下命令：

| 命令 | 说明 |
|------|------|
| `/start` | 启动机器人 |
| `/help` | 查看帮助 |
| `/aris 内容` | 开启多轮对话（计入记忆） |
| `/ask 内容` | 单次快速问答（不计入记忆） |
| `/reset` | 重置对话历史和状态 |
| `/model 模型名` | 切换模型 |
| `/setkey groq gsk_xxx` | 配置 Groq API Key |
| `/setkey gemini AI_xxx` | 配置 Gemini API Key |
| `/setapi groq` | 切换到 Groq 引擎 |
| `/setapi gemini` | 切换到 Gemini 引擎 |

## 7. 常见问题

### 7.1 机器人不能收到 QQ 消息

- 检查 OneBot 框架是否已启动并登录 QQ
- 确认 `QQ_BOT_PORT` 与框架的上报地址一致
- 确认 OneBot 框架将消息事件正确推送到 `http://127.0.0.1:8080`

### 7.2 机器人发送消息失败

- 检查 `QQ_BOT_API_URL` 是否正确
- 确认你可以直接访问 `QQ_BOT_API_URL/send_msg`
- 查看框架日志是否有发送失败的错误

### 7.3 找不到 bot 账号

QQ 上没有像 Telegram 那样的机器人目录。你需要：

- 找到你登录到 OneBot 框架的 QQ 号
- 用你的个人 QQ 加该号为好友，或把它拉入群

## 8. 进阶说明

如果你希望进一步优化：

- 让群聊仅在 @ 时才回复
- 支持更多 OneBot 事件类型（如图片、语音、回复）
- 支持 QQ Bot 直接读取群成员昵称

你可以在 `qq_main.py` 中扩展 `_handle_event` 和消息解析逻辑。
