import os
from groq import Groq
from dotenv import load_dotenv

def classify(model_id: str) -> str:
    mid = model_id.lower()
    if any(k in mid for k in ("whisper", "tts", "orpheus")):
        return "🎵 音频"
    if any(k in mid for k in ("guard", "safeguard")):
        return "🛡️ 安全"
    if any(k in mid for k in ("vision", "-vl", "scout", "maverick")):
        return "👁️ 视觉"
    return "💬 文本"

def fmt_ctx(model) -> str:
    n = (getattr(model, "context_window", None)
         or getattr(model, "context_length", None)
         or getattr(model, "max_tokens", None))
    if not n:
        return "—"
    return f"{n // 1000}k" if n >= 1000 else str(n)

def check_models():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ 未在 .env 中找到 GROQ_API_KEY")
        return

    client = Groq(api_key=api_key)

    try:
        models = sorted(client.models.list().data, key=lambda m: m.id)
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return

    # 按类型分组
    groups = {}
    for m in models:
        t = classify(m.id)
        groups.setdefault(t, []).append(m)

    total = len(models)
    summary = "  |  ".join(f"{t} {len(v)}" for t, v in sorted(groups.items()))
    print(f"\n共 {total} 个模型  —  {summary}\n")

    for group_name in ["💬 文本", "👁️ 视觉", "🎵 音频", "🛡️ 安全"]:
        group = groups.get(group_name)
        if not group:
            continue
        print(f"{group_name} ({len(group)})")
        print(f"  {'模型 ID':<50} {'context':>8}  {'所有方'}")
        print(f"  {'─'*50} {'─'*8}  {'─'*20}")
        for m in group:
            mid = m.id if len(m.id) <= 50 else m.id[:47] + "..."
            print(f"  {mid:<50} {fmt_ctx(m):>8}  {m.owned_by or '—'}")
        print()

if __name__ == "__main__":
    check_models()