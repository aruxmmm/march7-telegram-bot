from openai import OpenAI
from google import genai
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
    获取对应的 API 客户端实例
    """
    # 1. 确定 Provider 逻辑保持不变...
    if api_provider is None:
        if DB_AVAILABLE:
            api_provider = get_user_api_provider(user_id)
        else:
            api_provider = user_api_provider.get(user_id, "groq")
    
    # 2. 获取对应的 API Key
    if DB_AVAILABLE:
        user_keys_dict = get_user_api_keys(user_id)
    else:
        user_keys_dict = user_keys.get(user_id) if isinstance(user_keys.get(user_id), dict) else {}

    if api_provider == "gemini":
        # 获取 Gemini Key
        custom_key = user_keys_dict.get("gemini") if user_keys_dict else None
        target_key = custom_key if custom_key else GEMINI_API_KEY
        if not target_key:
            raise ValueError("Gemini API Key 未配置")
        
        # --- 关键修改点：不再 return "gemini"，而是返回 Client 实例 ---
        return genai.Client(api_key=target_key)
        
    else:
        # 获取 Groq Key
        custom_key = user_keys_dict.get("groq") if user_keys_dict else None
        # 兼容性处理：如果 user_keys[user_id] 直接就是字符串（旧格式）
        if not custom_key and isinstance(user_keys.get(user_id), str):
            custom_key = user_keys.get(user_id)
            
        target_key = custom_key if custom_key else GROQ_API_KEY
        if not target_key:
            raise ValueError("Groq API Key 未配置")
            
        return OpenAI(
            api_key=target_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
def generate_reply(user_input, user_id, use_memory=True):
    # 1. 获取基本状态和模型配置
    state = get_state(user_id)
    memory = get_memory(user_id) if use_memory else "（本次为单次提问模式）"
    
    # 2. 确定用户要用哪个模型
    user_model_key = user_model.get(user_id, "fast")
    if user_model_key in DEFAULT_MODELS:
        user_model_key = DEFAULT_MODELS[user_model_key]
    
    # 3. 【关键步】先拿到 api_provider 和 model_name
    model_config = MODEL_LIST.get(user_model_key, MODEL_LIST["groq_fast"])
    api_provider = model_config["api"]    # 这里赋值了！
    model_name = model_config["model"]    # 确保这里是 gemini-2.5-flash
    
    # 4. 现在再传给 get_client 就不报错了
    client = get_client(user_id, api_provider)
    
    prompt = get_prompt(state, memory, user_input)

    try:
        if api_provider == "gemini":
            # 新版 SDK 的写法
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        else:
            # Groq/OpenAI 写法
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            return response.choices[0].message.content
    except Exception as e:
        # 你的错误处理逻辑...
      error_str = str(e).lower()
      full_error = str(e)[:300]  # 保留更多错误信息用于调试
    
      if "403" in error_str or "forbidden" in error_str:
        if "model" in error_str or "permission" in error_str:
            msg = "「这个模型本姑娘暂时用不了呢... 试试换个模型？用 /model 看看」"
        elif any(k in error_str for k in ["key", "auth", "authentication", "invalid"]):
            msg = "「能量块（API Key）好像有问题～ 检查一下 /setkey 设置的对不对？或者试试切换回公共额度」"
        elif "cloudflare" in error_str or "access denied" in error_str or "network" in error_str:
            msg = "「信号被 Cloudflare 挡住了（403 Forbidden）... 可能是网络或服务器 IP 问题，换个网络/VPN 试试？」"
        else:
            msg = "「信号被挡住了（403 Forbidden）... 可能是权限或网络问题，等会儿再试试吧」"
      elif "429" in error_str or "rate limit" in error_str:
        msg = "「本姑娘今天被问太多次，脑子有点累了～ 等会儿再来找我玩吧！」"
      elif "401" in error_str or "unauthorized" in error_str:
        msg = "「能量块验证失败了呢... 请用 /setkey 重新告诉我正确的 Key」"
      else:
        msg = "（相机突然卡住了...）「呜，信号不太好呢~」"
        # 返回给用户
      return f"{msg}\n\n(调试信息: {full_error})"
    
    