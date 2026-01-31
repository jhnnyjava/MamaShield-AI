"""
Cultural knowledge module for Kalenjin/Bomet maternal health practices.
Based on rural studies and traditional pregnancy beliefs in Bomet, Kenya.
"""

# Kalenjin pregnancy nutrition - Traditional recommendations
KALENJIN_RECOMMENDED_FOODS = {
    "vegetables": {
        "items": ["sukuma wiki", "managu", "mitoo", "traditional greens"],
        "benefits": "Rich in iron for blood, prevents anemia",
        "kalenjin_name": "sukuma, managu, mitoo"
    },
    "milk": {
        "items": ["fresh milk", "fermented milk (mursik)"],
        "benefits": "Strong bones for mama and baby, 63% preference in Bomet",
        "kalenjin_name": "mwaiti"
    },
    "fruits": {
        "items": ["bananas", "oranges", "local fruits"],
        "benefits": "Vitamins and energy",
        "kalenjin_name": "fruits"
    },
    "traditional_herbs": {
        "items": ["herbal teas", "traditional remedies"],
        "benefits": "34% use for health, consult CHW for safety",
        "kalenjin_name": "traditional herbs"
    },
    "ugali_porridge": {
        "items": ["ugali", "uji (porridge)", "githeri"],
        "benefits": "Energy and strength for delivery",
        "kalenjin_name": "ugali, uji"
    },
    "liver": {
        "items": ["liver"],
        "benefits": "Iron for blood",
        "kalenjin_name": "liver"
    }
}

# Foods avoided in Kalenjin pregnancy culture (>60% avoidance)
KALENJIN_AVOIDED_FOODS_HIGH = {
    "animal_organs": {
        "items": ["tongue", "heart", "udder", "male reproductive organs"],
        "traditional_reason": "Fear of big fetus, difficult birth, baby colic, poor skin",
        "advice": "These beliefs are cultural. Modern evidence shows organ meat is nutritious, but respect your tradition. Focus on liver instead."
    },
    "meat": {
        "items": ["excessive meat", "certain meats"],
        "traditional_reason": "Fear of big baby, hard labor",
        "advice": "Small amounts of meat are safe and provide iron. Balance with vegetables."
    },
    "eggs": {
        "items": ["eggs"],
        "traditional_reason": "Fear of big baby, difficult delivery",
        "advice": "Eggs are very nutritious for pregnancy. If you choose to avoid, ensure protein from milk and beans."
    }
}

# Foods avoided by 20-40% (moderate avoidance)
KALENJIN_AVOIDED_FOODS_MODERATE = {
    "avocado": {
        "items": ["avocado"],
        "traditional_reason": "Fear of miscarriage, stillbirth",
        "advice": "No evidence of harm. Avocados are healthy fats, but respect your comfort level."
    },
    "oily_foods": {
        "items": ["fried foods", "very oily foods"],
        "traditional_reason": "Fear of maternal death, complications",
        "advice": "Excessive oil isn't healthy, but some fat is needed. Choose healthy fats like milk."
    }
}

# Core cultural values
KALENJIN_PREGNANCY_VALUES = [
    "Protect mother and child health",
    "Ensure easy delivery (light baby preferred)",
    "Prevent complications",
    "Traditional wisdom from elders",
    "Community support and sharing"
]


def get_cultural_food_advice(food_query: str = None) -> str:
    """
    Get culturally appropriate food advice for Kalenjin mothers.
    
    Args:
        food_query: Optional specific food question
    
    Returns:
        Cultural advice string
    """
    advice = []
    
    # Recommended foods
    advice.append("✅ RECOMMENDED (Kalenjin tradition):")
    advice.append(f"• Mwaiti (milk) - {KALENJIN_RECOMMENDED_FOODS['milk']['benefits']}")
    advice.append(f"• Managu, sukuma wiki - {KALENJIN_RECOMMENDED_FOODS['vegetables']['benefits']}")
    advice.append(f"• Ugali, uji - {KALENJIN_RECOMMENDED_FOODS['ugali_porridge']['benefits']}")
    advice.append(f"• Liver - {KALENJIN_RECOMMENDED_FOODS['liver']['benefits']}")
    
    # Culturally avoided foods
    advice.append("\n⚠️ TRADITIONALLY AVOIDED:")
    advice.append("• Animal organs, eggs - (elders say: big baby, hard labor)")
    advice.append("• Avocado, oily foods - (elders say: complications risk)")
    advice.append("\n💡 Balance tradition with health: Some avoided foods are nutritious. Discuss with CHW.")
    
    return "\n".join(advice)


def get_kalenjin_phrase(context: str) -> str:
    """
    Get culturally appropriate Kalenjin/English phrase for context.
    
    Args:
        context: Context like 'milk', 'vegetables', 'strength'
    
    Returns:
        Culturally appropriate phrase
    """
    phrases = {
        "milk": "Drink mwaiti (milk) for strong bones",
        "vegetables": "Eat managu and sukuma wiki for healthy blood",
        "strength": "Eat ugali and uji for energy during delivery",
        "herbs": "Traditional herbs can help, but check with CHW first",
        "baby_size": "Our elders prefer light babies for easy delivery - this is safe and wise",
        "avoid_eggs": "Many Kalenjin women avoid eggs for tradition - ensure protein from beans and mwaiti",
        "anc": "Attend ANC at clinic - blend modern care with traditional wisdom"
    }
    
    return phrases.get(context, "")


def is_culturally_sensitive_topic(text: str) -> bool:
    """
    Check if the message relates to culturally sensitive topics.
    
    Args:
        text: User message
    
    Returns:
        True if culturally sensitive
    """
    sensitive_keywords = [
        "food", "eat", "nutrition", "milk", "mwaiti", "egg", "meat",
        "avocado", "vegetables", "managu", "sukuma", "ugali", "what can i eat",
        "what should i eat", "avoid", "traditional", "elders", "culture"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in sensitive_keywords)
