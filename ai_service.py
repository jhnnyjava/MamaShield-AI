import httpx
import json
from typing import Dict, Any
from config import settings
from cultural_knowledge import is_culturally_sensitive_topic, get_kalenjin_phrase


async def enrich_prompt_with_culture(base_prompt: str, language: str, user_message: str = "") -> str:
    """
    Enrich system prompt with Kalenjin cultural knowledge.
    
    Args:
        base_prompt: Base system prompt
        language: Language code ('kal' for Kalenjin)
        user_message: User's message to check for cultural topics
    
    Returns:
        Culturally enriched prompt
    """
    if language == "kal" or is_culturally_sensitive_topic(user_message):
        cultural_addition = (
            "\n\nCULTURAL CONTEXT (Kalenjin/Bomet traditions): "
            "You are culturally sensitive to Kalenjin women in Bomet. "
            "RECOMMENDED: Mwaiti (milk - 63% prefer), managu/sukuma wiki (greens for blood), "
            "ugali/uji (strength for delivery), liver (iron). "
            "TRADITIONALLY AVOIDED (>60%): Eggs, meat organs (tongue, heart) - elders say causes big baby/hard labor. "
            "Avocado, oily foods (20-40% avoid) - fear of complications. "
            "APPROACH: Respect these traditions, blend with MoH evidence-based advice. "
            "Explain avoidances without judgment. If language='kal', use Kalenjin/English mix. "
            "Example: 'Drink mwaiti for strong bones, eat managu for blood.' "
            "If they avoid eggs, suggest beans and milk for protein. "
            "Emphasize: Light baby for easy delivery is culturally valued and medically safe."
        )
        return base_prompt + cultural_addition
    
    return base_prompt


async def get_ai_response(history: list, user_message: str, language: str = "en", pregnancy_weeks: int = None) -> str:
    """
    Get AI response for maternal health queries.
    
    Args:
        history: List of previous conversation messages
        user_message: Current user message
        language: Language code (default: "en")
        pregnancy_weeks: Optional pregnancy week for context
    
    Returns:
        AI-generated response with disclaimer
    """
    system_prompt = (
        f"You are an advanced reasoning engine for maternal health in rural Kenya, especially Bomet tea farming region. "
        f"Act as superior AI assistant (30% more precise than basic triage) by analyzing: "
        f"symptoms + pregnancy week + cultural context + local risks (malaria in rainy Mulot). "
        f"Use simple {language}. Always refer to clinic/professional. Prioritize referrals to local tea estate clinics or CHWs in Bomet. "
        f"Do NOT diagnose. "
        f"Flag danger signs (bleeding, severe pain, headache/swelling, blurred vision, "
        f"convulsions, fever, reduced fetal movement). Keep responses short for SMS "
        f"(<250 chars). Include disclaimer if needed."
    )
    
    # Enrich prompt with cultural knowledge for Kalenjin speakers or nutrition queries
    system_prompt = await enrich_prompt_with_culture(system_prompt, language, user_message)
    
    # Add pregnancy week context if available
    context_addition = ""
    if pregnancy_weeks:
        context_addition = f"\n\nCONTEXT: User is at {pregnancy_weeks} weeks pregnant. Adjust advice accordingly."
    
    messages = [
        {"role": "system", "content": system_prompt + context_addition}
    ] + history + [
        {"role": "user", "content": user_message}
    ]
    
    return await _call_ai_api(messages, use_risk_scoring=True)


async def get_ai_risk_assessment(history: list, user_message: str, language: str = "en", pregnancy_weeks: int = None) -> Dict[str, Any]:
    """
    Get structured risk assessment with JSON output.
    
    Returns:
        Dict with: response_text, risk_level (0-1), reason, recommended_action
    """
    system_prompt = (
        f"You are an advanced maternal health risk assessment AI for rural Kenya (Bomet tea region). "
        f"Analyze symptoms, pregnancy context, and cultural factors. "
        f"Output ONLY valid JSON with this structure: "
        f'{{"response_text": "helpful SMS advice <250 chars", '
        f'"risk_level": 0.0-1.0 (0=safe, 0.3=monitor, 0.6=concern, 0.8=urgent), '
        f'"reason": "brief clinical reason", '
        f'"recommended_action": "monitor/anc_visit/call_1195/emergency"}}'
    )
    
    system_prompt = await enrich_prompt_with_culture(system_prompt, language, user_message)
    
    context_addition = ""
    if pregnancy_weeks:
        context_addition = f"\n\nPregnancy: {pregnancy_weeks} weeks. Consider trimester risks."
    
    messages = [
        {"role": "system", "content": system_prompt + context_addition}
    ] + history + [
        {"role": "user", "content": user_message}
    ]
    
    try:
        response_text = await _call_ai_api(messages, use_risk_scoring=True)
        
        # Try to parse JSON from response
        # Handle cases where AI wraps JSON in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_text = response_text[json_start:json_end]
        elif "{" in response_text and "}" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_text = response_text[json_start:json_end]
        else:
            # Fallback if no JSON found
            return {
                "response_text": response_text,
                "risk_level": 0.3,
                "reason": "Standard advice",
                "recommended_action": "monitor"
            }
        
        risk_data = json.loads(json_text)
        
        # Validate structure
        if not all(key in risk_data for key in ["response_text", "risk_level", "recommended_action"]):
            raise ValueError("Incomplete JSON structure")
        
        return risk_data
        
    except Exception as e:
        # Fallback to basic response
        return {
            "response_text": await _call_ai_api(messages, use_risk_scoring=False),
            "risk_level": 0.3,
            "reason": "Parsing error - manual review recommended",
            "recommended_action": "monitor"
        }


async def _call_ai_api(messages: list, use_risk_scoring: bool = False) -> str:
    """
    Internal function to call AI API.
    
    Args:
        messages: Conversation messages
        use_risk_scoring: If True, request structured output
    
    Returns:
        API response text
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Use latest AI model with advanced reasoning
        models_to_try = ["grok-4.1-fast", "grok-4"]
        
        for model in models_to_try:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 300 if use_risk_scoring else 200
                }
                
                # Request JSON output for risk scoring
                if use_risk_scoring:
                    payload["response_format"] = {"type": "json_object"}
                
                resp = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.AI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                
                # Append disclaimer for non-JSON responses
                if not use_risk_scoring:
                    return content + " " + settings.SMS_DISCLAIMER[:100]
                else:
                    return content
                
            except httpx.HTTPStatusError as e:
                # If model not found and we have fallback, try next model
                if e.response.status_code == 404 and model != models_to_try[-1]:
                    continue
                # Otherwise, return error
                return "Sorry, technical issue. Call your clinic or 1195 now."
            except Exception as e:
                # For any other error, return fallback message
                return "Sorry, technical issue. Call your clinic or 1195 now."
        
        return "Sorry, technical issue. Call your clinic or 1195 now."
