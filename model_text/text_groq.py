import os
from groq import Groq
from dotenv import load_dotenv

def check_models():
    # 1. 从 .env 加载环境变量
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未在 .env 文件中找到 GROQ_API_KEY")
        return

    # 2. 初始化 Groq 客户端
    # 如果你在国内环境运行，且没有开启全局代理，可能需要在这里配置 httpx 的 proxy
    client = Groq(api_key=api_key)

    try:
        # 3. 获取模型列表
        models = client.models.list()
        
        print(f"{'模型 ID':<30} | {'开发者':<15} | {'上下文长度':<10}")
        print("-" * 60)
        
        for model in models.data:
            model_id = model.id
            owned_by = model.owned_by
            # 部分模型信息可能在 context_window 中，这里简单展示 ID
            print(f"{model_id:<30} | {owned_by:<15}")
            
    except Exception as e:
        print(f"❌ 获取模型列表失败: {e}")

if __name__ == "__main__":
    check_models()