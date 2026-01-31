from config import settings


def detect_danger_signs(text: str, language: str = "en") -> tuple[bool, str]:
    """
    Detect maternal health danger signs in user messages.
    
    Args:
        text: User message to analyze
        language: Language code ("en", "sw", or "kal")
    
    Returns:
        Tuple of (is_danger_detected, warning_message)
    """
    en_keywords = [
        "bleeding", "severe pain", "headache", "swelling", 
        "blurred vision", "convulsions", "fever", "reduced fetal movement"
    ]
    
    sw_keywords = [
        "damu", "maumivu makali", "kichwa", "uvimbe", 
        "kuona giza", "mshtuko", "homa", "mtoto ashangaa"
    ]
    
    # Kalenjin danger sign keywords
    kal_keywords = [
        "bleeding", "damu", "pain makali", "kichwa kuuma",
        "swelling", "vision", "convulsions", "homa", "baby not moving"
    ]
    
    if language == "kal":
        keywords = kal_keywords
    elif language == "sw":
        keywords = sw_keywords
    else:
        keywords = en_keywords
    
    text_lower = text.lower()
    
    for kw in keywords:
        if kw in text_lower:
            return True, f"Danger sign detected! Go to clinic NOW or call 1195. {settings.SMS_DISCLAIMER}"
    
    return False, None
