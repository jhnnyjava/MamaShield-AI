from fastapi import APIRouter, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import dateparser

from config import settings
from database import get_or_create_user, append_history, log_metric, update_user
from grok_service import get_grok_response
from sms_service import send_sms
from danger_detection import detect_danger_signs


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def process_message(phone: str, text: str) -> str:
    """
    Process incoming message (shared logic for SMS and USSD).
    Returns the AI response.
    """
    # Get or create user
    user = await get_or_create_user(phone)
    language = user.language or "en"
    
    # Check if this is an ANC poll response
    text_upper = text.strip().upper()
    if text_upper in ['Y', 'YES', 'N', 'NO']:
        if text_upper in ['Y', 'YES']:
            await log_metric("anc_poll_yes", {"language": language})
            return "Great! Keep attending your ANC visits. Your health matters!"
        else:
            await log_metric("anc_poll_no", {"language": language})
            return "Please visit your clinic soon for ANC checkup. It's important for you and baby."
    
    # Check for danger signs first
    is_danger, danger_msg = detect_danger_signs(text, language)
    if is_danger:
        await log_metric("danger_flag", {"language": language})
        
        # Alert CHW about high-risk case
        chw_alert = f"High-risk alert! User {phone[-4:]} reported danger signs. Call them immediately."
        await send_sms(settings.CHW_PHONE, chw_alert)
        
        await append_history(user.phone_hash, "user", text)
        await append_history(user.phone_hash, "assistant", danger_msg)
        return danger_msg
    
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
    
    # Update conversation history
    await append_history(user.phone_hash, "user", text)
    await append_history(user.phone_hash, "assistant", ai_response)
    
    return ai_response


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
        
        # Process message
        ai_response = await process_message(phone, text)
        
        # Send SMS response
        sms_result = await send_sms(phone, ai_response)
        if sms_result:
            await log_metric("message_sent")
        
        return {"status": "success", "response": ai_response}
        
    except Exception as e:
        error_msg = "Sorry, service unavailable. Please call your clinic or 1195."
        await send_sms(phone, error_msg)
        return {"status": "error", "message": str(e)}


@router.post("/ussd")
async def ussd_callback(
    request: Request,
    sessionId: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    serviceCode: str = Form(...)
):
    """
    USSD callback endpoint for Africa's Talking.
    
    Returns:
    - CON <message> - to continue session
    - END <message> - to end session
    """
    try:
        # First interaction - show main menu
        if text == "":
            response = "CON Welcome to MamaShield!\n1. Join/Register\n2. Get Pregnancy Tip\n3. Ask Question\n0. Exit"
        
        # User selected option 1 - Registration
        elif text == "1":
            response = "CON Reply with due date (YYYY-MM-DD) or weeks pregnant:"
        
        # User is providing registration data after selecting 1
        elif text.startswith("1*"):
            user_input = text.split("*", 1)[1]
            
            # Try to parse as date or weeks
            user = await get_or_create_user(phoneNumber)
            
            # Try parsing as date first
            parsed_date = dateparser.parse(user_input)
            if parsed_date:
                await update_user(user.phone_hash, pregnancy_due_date=parsed_date.date())
                response = "END Registered! Your due date is saved. Check SMS for tips."
                await log_metric("registration", {"via": "ussd"})
            else:
                # Try parsing as weeks
                try:
                    weeks = int(user_input)
                    await update_user(user.phone_hash, pregnancy_weeks=weeks)
                    response = "END Registered! You're at week {weeks}. Check SMS for tips."
                    await log_metric("registration", {"via": "ussd"})
                except:
                    response = "END Invalid input. Please try again via SMS."
        
        # User selected option 2 - Get tip
        elif text == "2":
            tip = "Eat healthy, rest well, attend ANC. Check SMS for personalized advice!"
            response = f"END {tip}"
            await log_metric("ussd_tip_request")
        
        # User selected option 3 - Ask question
        elif text == "3":
            response = "CON Ask your question:"
        
        # User is asking a question after selecting 3
        elif text.startswith("3*"):
            question = text.split("*", 1)[1]
            await log_metric("message_received", {"via": "ussd"})
            
            # Process the question
            ai_response = await process_message(phoneNumber, question)
            
            # Send full response via SMS
            await send_sms(phoneNumber, ai_response)
            await log_metric("message_sent", {"via": "ussd"})
            
            response = "END Thank you! Check SMS for detailed answer."
        
        # User selected exit
        elif text == "0":
            response = "END Thank you for using MamaShield! Stay healthy."
        
        # Unknown option
        else:
            response = "END Invalid option. Dial again to try."
        
        return response
        
    except Exception as e:
        return "END Service error. Please try again or SMS us."
