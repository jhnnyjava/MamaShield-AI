"""
CHW referral and tea farm integration module for MamaShield AI.
Unique feature for Bomet tea farming region.
"""
import asyncio
from config import settings
from sms_service import send_sms
from database import log_metric


async def send_chw_alert(phone: str, danger_signs: str, user_location: str = "Mulot tea zone"):
    """
    Send high-risk alert to CHW for urgent follow-up.
    
    Args:
        phone: User's phone number (last 4 digits will be shared)
        danger_signs: Description of danger signs detected
        user_location: User's location area
    """
    try:
        chw_message = (
            f"ALERT: High-risk pregnancy reported. "
            f"Masked user {phone[-4:]} mentioned {danger_signs}. "
            f"Contact urgently. Location area: {user_location}."
        )
        
        # Send to primary CHW
        await send_sms(settings.CHW_PHONE, chw_message)
        
        # If tea farm CHW is configured, send there too
        if hasattr(settings, 'TEA_CHW_PHONE') and settings.TEA_CHW_PHONE:
            await send_sms(settings.TEA_CHW_PHONE, chw_message)
        
        # Log the referral
        await log_metric("chw_referral", {
            "location": user_location,
            "signs": danger_signs[:50]  # Truncate for privacy
        })
        
        return True
        
    except Exception as e:
        print(f"CHW alert error: {e}")
        return False


async def send_farm_clinic_referral(phone: str, reason: str = "ANC checkup"):
    """
    Send referral to tea farm clinic.
    
    Args:
        phone: User's phone number
        reason: Reason for referral
    """
    try:
        if hasattr(settings, 'FARM_CLINIC_NUMBER') and settings.FARM_CLINIC_NUMBER:
            clinic_message = (
                f"Referral: Pregnant woman from tea estate needs {reason}. "
                f"Contact {phone[-4:]} for appointment. MamaShield AI referral."
            )
            
            await send_sms(settings.FARM_CLINIC_NUMBER, clinic_message)
            await log_metric("farm_clinic_referral", {"reason": reason})
            
            return True
    except Exception as e:
        print(f"Farm clinic referral error: {e}")
        return False


async def send_anc_visit_thank_you(phone: str, language: str = "en"):
    """
    Send thank you message after confirmed ANC visit.
    Creates positive reinforcement and data for cooperative reports.
    
    Args:
        phone: User's phone number
        language: User's language preference
    """
    try:
        if language == "kal":
            message = "Kongoi! (Thank you!) Great job attending ANC. Keep it up for healthy pregnancy! Drink mwaiti and rest well."
        else:
            message = "Thank you for attending ANC! You're taking great care of yourself and baby. Keep going to all visits!"
        
        await send_sms(phone, message)
        await log_metric("anc_visit_confirmed", {"language": language})
        
        return True
        
    except Exception as e:
        print(f"Thank you SMS error: {e}")
        return False


def get_farm_specific_tips(season: str = "picking", language: str = "en") -> str:
    """
    Get farm-specific pregnancy tips for tea workers.
    
    Args:
        season: Farm season (picking, pruning, etc.)
        language: Language preference
    
    Returns:
        Farm-specific advice
    """
    tips = {
        "picking": {
            "en": "During tea picking: Take breaks every hour, stay hydrated (drink mwaiti/water), avoid heavy lifting. Ask supervisor for lighter tasks if tired.",
            "kal": "Wakati wa kuchuma chai: Rest often, drink mwaiti (milk) na maji, don't carry heavy baskets when pregnant. Tell supervisor if you feel tired."
        },
        "general": {
            "en": "Tea farm moms: Wear comfortable shoes, use sun protection, drink plenty of fluids. Report any dizziness to CHW at farm clinic.",
            "kal": "Mama wa shamba chai: Drink mwaiti, rest when tired, protect from sun. If dizzy, go to clinic haraka (quickly)."
        }
    }
    
    season_key = season if season in tips else "general"
    return tips[season_key].get(language, tips[season_key]["en"])


async def track_farm_worker_engagement(phone_hash: str, activity: str):
    """
    Track tea farm worker engagement for KTDA/Unilever partnership reports.
    
    Args:
        phone_hash: Hashed phone number
        activity: Type of engagement (onboarding, anc_visit, referral, etc.)
    """
    await log_metric("tea_farm_engagement", {
        "activity": activity,
        "partnership_tracking": True
    })
