import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class GrokClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROK_API_KEY"),
            base_url="https://api.x.ai/v1"
        )
    
    async def generate(self, messages, model="grok-4-20", temperature=0.9, max_tokens=800):
        """统一生成回复，和 text_gemini.py 的风格保持一致"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Grok API Error] {e}")
            return "哎呀……脑子突然短路了，主人再试一次嘛～"