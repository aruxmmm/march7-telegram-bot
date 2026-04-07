import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# 获取 Key 并打印前四位（仅用于调试，确认读取成功）
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print(f"API Key 读取成功: {api_key[:4]}****")
else:
    print("API Key 读取失败，请检查 .env 文件！")

# 使用新版 SDK 初始化客户端
client = genai.Client(api_key=api_key)

try:
    print("正在尝试获取模型列表...")
    # 新版获取模型的方法
    for m in client.models.list():
        print(f"可用模型: {m.name}")
        
    # 测试生成
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents="你好，三月七！"
    )
    print(f"回复内容: {response.text}")
    
except Exception as e:
    print(f"仍然遇到错误: {e}")
    test_models = ["gemini-1.5-flash-latest", "gemini-2.5-flash-lite-preview", "gemini-1.5-pro-latest"]

for model_name in test_models:
    try:
        print(f"尝试调用: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="测试一下，能听到吗？"
        )
        print(f"✅ {model_name} 可以使用！回复: {response.text}")
        break # 找到能用的就跳出
    except Exception as e:
        print(f"❌ {model_name} 失败: {e}\n")