from main import DISCLAIMER


def detect_danger_signs(text: str, language: str = "en") -> tuple[bool, str]:
    """
    Detect maternal health danger signs in user messages.
    
    Args:
        text: User message to analyze
        language: Language code ("en" or "sw")
    
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
    
    keywords = en_keywords if language == "en" else sw_keywords
    text_lower = text.lower()
    
    for kw in keywords:
        if kw in text_lower:
            return True, f"Danger sign detected! Go to clinic NOW or call 1195. {DISCLAIMER}"
    
    return False, None
