import asyncio
import africastalking
from config import settings


# Initialize Africa's Talking SDK
africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
sms = africastalking.SMS


async def send_sms(phone: str, message: str):
    """
    Send SMS using Africa's Talking API.
    
    Args:
        phone: Recipient phone number (E.164 format recommended)
        message: SMS message content
    
    Returns:
        API response or None on error
    """
    try:
        response = await asyncio.to_thread(
            sms.send,
            message=message,
            recipients=[phone]
        )
        return response
    except Exception as e:
        print(f"SMS error: {e}")
        return None
