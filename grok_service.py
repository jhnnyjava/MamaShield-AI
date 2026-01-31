import httpx
from config import settings


async def get_grok_response(history: list, user_message: str, language: str = "en") -> str:
    """
    Get AI response from Grok API for maternal health queries.
    
    Args:
        history: List of previous conversation messages
        user_message: Current user message
        language: Language code (default: "en")
    
    Returns:
        AI-generated response with disclaimer
    """
    system_prompt = (
        f"You are a safe, helpful maternal health assistant for rural Kenya. "
        f"Use simple {language}. Always refer to clinic/professional. Do NOT diagnose. "
        f"Flag danger signs (bleeding, severe pain, headache/swelling, blurred vision, "
        f"convulsions, fever, reduced fetal movement). Keep responses short for SMS "
        f"(<250 chars). Include disclaimer if needed."
    )
    
    messages = [
        {"role": "system", "content": system_prompt}
    ] + history + [
        {"role": "user", "content": user_message}
    ]
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-4",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 200
                }
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            
            # Append disclaimer (truncate if too long)
            return content + " " + settings.SMS_DISCLAIMER[:100]
            
        except Exception as e:
            return "Sorry, technical issue. Call your clinic or 1195 now."
