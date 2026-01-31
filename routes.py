from fastapi import APIRouter, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import dateparser

from config import settings
from database import get_or_create_user, append_history, log_metric, update_user
from ai_service import get_ai_response, get_ai_risk_assessment
from sms_service import send_sms
from danger_detection import detect_danger_signs
from chw_referral import send_chw_alert, send_anc_visit_thank_you, get_farm_specific_tips, track_farm_worker_engagement


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
    
    # Check if user is identifying as tea farm worker
    text_upper = text.strip().upper()
    if text_upper == "TEA":
        await update_user(user.phone_hash, is_tea_farm_worker=1, language="kal")
        await track_farm_worker_engagement(user.phone_hash, "onboarding")
        farm_tips = get_farm_specific_tips("picking", "kal")
        response = f"Welcome tea farm mama! {farm_tips} We'll send you special tips for farm workers."
        await log_metric("tea_farm_registration")
        return response
    
    # Check for feedback responses
    if text_upper in ['HELPFUL', 'NOT HELPFUL'] or (len(text_upper) <= 20 and ('HELP' in text_upper or 'YES' in text_upper or 'NO' in text_upper)):
        feedback_value = "positive" if any(word in text_upper for word in ['YES', 'Y', 'HELPFUL', 'GOOD']) else "negative"
        await log_metric("feedback_received", {"sentiment": feedback_value, "language": language})
        await append_history(user.phone_hash, "feedback", feedback_value)
        return "Thank you for your feedback! It helps us improve MamaShield for all mamas."
    
    # Check if this is an ANC poll response
    if text_upper in ['Y', 'YES', 'N', 'NO']:
        if text_upper in ['Y', 'YES']:
            await log_metric("anc_poll_yes", {"language": language})
            
            # Send thank you for ANC visit (referral incentive)
            await send_anc_visit_thank_you(phone, language)
            
            # Track for tea farm workers (KTDA partnership data)
            if user.is_tea_farm_worker:
                await track_farm_worker_engagement(user.phone_hash, "anc_visit")
            
            return "Great! Keep attending your ANC visits. Your health matters!"
        else:
            await log_metric("anc_poll_no", {"language": language})
            return "Please visit your clinic soon for ANC checkup. It's important for you and baby."
    
    # Check for danger signs first
    is_danger, danger_msg = detect_danger_signs(text, language)
    if is_danger:
        await log_metric("danger_flag", {"language": language})
        
        # Send enhanced CHW alert with location context
        location = "Mulot tea zone" if user.is_tea_farm_worker else "Bomet area"
        await send_chw_alert(phone, text[:100], location)
        
        await append_history(user.phone_hash, "user", text)
        await append_history(user.phone_hash, "assistant", danger_msg)
        return danger_msg
    
    # Get conversation history
    history = user.history or []
    pregnancy_weeks = user.pregnancy_weeks
    
    # Use advanced AI risk assessment for better precision
    risk_assessment = await get_grok_risk_assessment(history, text, language, pregnancy_weeks)
    
    ai_response = risk_assessment.get("response_text", "Please visit your clinic for checkup.")
    risk_level = risk_assessment.get("risk_level", 0.3)
    recommended_action = risk_assessment.get("recommended_action", "monitor")
    
    # Auto-trigger CHW alert for high-risk cases (>0.6)
    if risk_level > 0.6:
        await log_metric("high_risk_detected", {"risk_level": risk_level, "action": recommended_action})
        location = "Mulot tea zone" if user.is_tea_farm_worker else "Bomet area"
        risk_reason = risk_assessment.get("reason", "High risk detected by AI")
        await send_chw_alert(phone, f"{text[:50]} - Risk: {risk_reason}", location)
        
        # Add urgent notice to response
        if recommended_action == "emergency" or risk_level > 0.8:
            ai_response = f"URGENT: {ai_response} Call 1195 or go to clinic NOW."
    
    # Increment interaction count
    interaction_count = (user.interaction_count or 0) + 1
    await update_user(user.phone_hash, interaction_count=interaction_count)
    
    # First interaction - ask about tea farm work
    if interaction_count == 1:
        ai_response += " Reply TEA if you work/pick tea - get special tips for farm moms."
    
    # Send feedback poll every 5 interactions
    if interaction_count % 5 == 0:
        feedback_poll = "Was our advice helpful? Reply YES or NO."
        ai_response += f" {feedback_poll}"
        await log_metric("feedback_poll_sent")
    
    # Send ANC poll every 4 interactions
    elif interaction_count % 4 == 0:
        anc_poll = "Did you attend ANC this month? Reply Y for yes, N for no."
        ai_response += f" {anc_poll}"
    
    # Add farm-specific tips for tea workers every 3 interactions
    if user.is_tea_farm_worker and interaction_count % 3 == 0:
        farm_tip = get_farm_specific_tips("picking", language)
        ai_response += f" Farm tip: {farm_tip[:80]}..."
    
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
