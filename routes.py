from fastapi import APIRouter, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_or_create_user, append_history
from grok_service import get_grok_response
from sms_service import send_sms
from danger_detection import detect_danger_signs


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/sms")
@limiter.limit("10/minute")
async def receive_sms(
    request: Request,
    phone: str = Form(..., alias="from"),
    text: str = Form(...)
):
    """
    Webhook endpoint for receiving SMS from Africa's Talking.
    
    Expects form data with:
    - from: sender's phone number
    - text: message content
    """
    try:
        # Get or create user
        user = await get_or_create_user(phone)
        language = user.language or "en"
        
        # Check for danger signs first
        is_danger, danger_msg = detect_danger_signs(text, language)
        if is_danger:
            await send_sms(phone, danger_msg)
            await append_history(user.phone_hash, "user", text)
            await append_history(user.phone_hash, "assistant", danger_msg)
            return {"status": "danger_alert_sent"}
        
        # Get conversation history
        history = user.history or []
        
        # Get AI response from Grok
        ai_response = await get_grok_response(history, text, language)
        
        # Send SMS response
        await send_sms(phone, ai_response)
        
        # Update conversation history
        await append_history(user.phone_hash, "user", text)
        await append_history(user.phone_hash, "assistant", ai_response)
        
        return {"status": "success", "response": ai_response}
        
    except Exception as e:
        error_msg = "Sorry, service unavailable. Please call your clinic or 1195."
        await send_sms(phone, error_msg)
        return {"status": "error", "message": str(e)}
