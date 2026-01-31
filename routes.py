from fastapi import APIRouter, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from database import get_or_create_user, append_history, log_metric, update_user
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
        # Log incoming message
        await log_metric("message_received")
        
        # Get or create user
        user = await get_or_create_user(phone)
        language = user.language or "en"
        
        # Check if this is an ANC poll response
        text_upper = text.strip().upper()
        if text_upper in ['Y', 'YES', 'N', 'NO']:
            if text_upper in ['Y', 'YES']:
                await log_metric("anc_poll_yes", {"language": language})
                response = "Great! Keep attending your ANC visits. Your health matters!"
            else:
                await log_metric("anc_poll_no", {"language": language})
                response = "Please visit your clinic soon for ANC checkup. It's important for you and baby."
            
            await send_sms(phone, response)
            await log_metric("message_sent")
            await append_history(user.phone_hash, "user", text)
            await append_history(user.phone_hash, "assistant", response)
            return {"status": "anc_poll_response"}
        
        # Check for danger signs first
        is_danger, danger_msg = detect_danger_signs(text, language)
        if is_danger:
            await log_metric("danger_flag", {"language": language})
            
            # Send alert to user
            await send_sms(phone, danger_msg)
            await log_metric("message_sent")
            
            # Alert CHW about high-risk case
            chw_alert = f"High-risk alert! User {phone[-4:]} reported danger signs. Call them immediately."
            await send_sms(settings.CHW_PHONE, chw_alert)
            
            await append_history(user.phone_hash, "user", text)
            await append_history(user.phone_hash, "assistant", danger_msg)
            return {"status": "danger_alert_sent"}
        
        # Get conversation history
        history = user.history or []
        
        # Get AI response from Grok
        ai_response = await get_grok_response(history, text, language)
        
        # Increment interaction count
        interaction_count = (user.interaction_count or 0) + 1
        await update_user(user.phone_hash, interaction_count=interaction_count)
        
        # Send ANC poll every 4 interactions
        if interaction_count % 4 == 0:
            anc_poll = "Did you attend ANC this month? Reply Y for yes, N for no."
            ai_response += f" {anc_poll}"
        
        # Send SMS response
        sms_result = await send_sms(phone, ai_response)
        if sms_result:
            await log_metric("message_sent", {"language": language})
        
        # Update conversation history
        await append_history(user.phone_hash, "user", text)
        await append_history(user.phone_hash, "assistant", ai_response)
        
        return {"status": "success", "response": ai_response}
        
    except Exception as e:
        error_msg = "Sorry, service unavailable. Please call your clinic or 1195."
        await send_sms(phone, error_msg)
        return {"status": "error", "message": str(e)}
