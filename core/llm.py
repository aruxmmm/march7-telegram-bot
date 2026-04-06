from openai import OpenAI
import google.generativeai as genai
from core.state import user_model, get_state
from core.memory import get_memory
from config import GROQ_API_KEY, GEMINI_API_KEY, MODEL_LIST, DEFAULT_MODELS, user_keys, user_api_provider
from prompt.march7 import get_prompt

# 导入数据库函数
try:
    from core.database import get_user_api_keys, get_user_api_provider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

def get_client(user_id, api_provider=None):
    """
    根据用户 ID 和 API 供应商获取对应的客户端
    api_provider: "groq" 或 "gemini"，如不指定则根据用户配置选择
    """
    # 确定使用的 API 供应商
    if api_provider is None:
        if DB_AVAILABLE:
            api_provider = get_user_api_provider(user_id)
        else:
            api_provider = user_api_provider.get(user_id, "groq")
    
    if api_provider == "gemini":
        # Gemini API 配置
        # 优先从数据库读取
        if DB_AVAILABLE:
            user_keys_dict = get_user_api_keys(user_id)
            custom_key = user_keys_dict.get("gemini") if user_keys_dict else None
        else:
            custom_key = user_keys.get(user_id, {}).get("gemini") if isinstance(user_keys.get(user_id), dict) else None
        
        target_key = custom_key if custom_key else GEMINI_API_KEY
        if not target_key:
            raise ValueError("Gemini API Key 未配置")
        genai.configure(api_key=target_key)
        return "gemini"
    else:
        # Groq API 配置（默认）
        # 优先从数据库读取
        if DB_AVAILABLE:
            user_keys_dict = get_user_api_keys(user_id)
            custom_key = user_keys_dict.get("groq") if user_keys_dict else None
        else:
            custom_key = user_keys.get(user_id, {}).get("groq") if isinstance(user_keys.get(user_id), dict) else user_keys.get(user_id)
        
        target_key = custom_key if custom_key else GROQ_API_KEY
        if not target_key:
            raise ValueError("Groq API Key 未配置")
        return OpenAI(
            api_key=target_key,
            base_url="https://api.groq.com/openai/v1"
        )

def generate_reply(user_input, user_id, use_memory=True):
    state = get_state(user_id)
    memory = get_memory(user_id) if use_memory else "（本次为单次提问模式）"
    
    # 获取用户选择的模型（兼容旧格式）
    user_model_key = user_model.get(user_id, "fast")
    if user_model_key in DEFAULT_MODELS:
        user_model_key = DEFAULT_MODELS[user_model_key]
    
    model_config = MODEL_LIST.get(user_model_key, MODEL_LIST["groq_fast"])
    api_provider = model_config["api"]
    model_name = model_config["model"]
    
    prompt = get_prompt(state, memory, user_input)

    try:
        if api_provider == "gemini":
            # 使用 Gemini API
            get_client(user_id, "gemini")  # 配置 API
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        else:
            # 使用 Groq API
            client = get_client(user_id, "groq")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"(哎呀，相机卡住了...) 「信号不太好呢，等下再说吧！」 (Error: {e})"