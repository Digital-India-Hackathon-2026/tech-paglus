from typing import Any
from services.agent_memory import get_feedback_history

def learn_preferences(farmer_name: str) -> dict[str, Any]:
    """
    Scans the feedback history for a farmer and learns preferences:
    - crop_boosts: Dict[str, float] mapping crop names to score adjustments
    - explanation_style: 'simple' or 'detailed'
    - risk_preference: 'conservative' or 'normal'
    - speed_multiplier: speed rate for TTS
    """
    history = get_feedback_history(farmer_name)
    crop_boosts = {}
    
    # Defaults
    explanation_style = "detailed"
    risk_preference = "normal"
    speed_multiplier = 0.9  # Default speed
    
    if not history:
        return {
            "crop_boosts": crop_boosts,
            "explanation_style": explanation_style,
            "risk_preference": risk_preference,
            "speed_multiplier": speed_multiplier
        }
        
    thumbs_up_count = 0
    thumbs_down_count = 0
    
    # Process history
    for item in history:
        crop = item["crop"].lower()
        useful = item["useful"]
        rating = item["rating"]
        
        # Crop specific adjustments
        if useful:
            thumbs_up_count += 1
            # Boost crop if rated highly
            crop_boosts[crop] = crop_boosts.get(crop, 0) + (5 * rating)
        else:
            thumbs_down_count += 1
            # Penalize crop
            crop_boosts[crop] = crop_boosts.get(crop, 0) - 25
            
        # Try to infer explanation style based on comments length or patterns
        comments = (item.get("comments") or "").lower()
        if "simple" in comments or "short" in comments or "clear" in comments:
            explanation_style = "simple"
        elif "detail" in comments or "explain" in comments or "why" in comments:
            explanation_style = "detailed"
            
        # Try to infer risk preferences
        if "risk" in comments or "failed" in comments or "loss" in comments:
            risk_preference = "conservative"
            
    # Normalize crop boosts to avoid infinite inflation (cap at [-30, +30])
    for crop in crop_boosts:
        crop_boosts[crop] = max(-30, min(30, crop_boosts[crop]))
        
    # Tone and speaking speed adjustments based on rating trend
    # If the farmer gives low ratings on average, slow down and use simpler terms
    avg_rating = sum(item["rating"] for item in history) / len(history)
    if avg_rating < 3.0:
        speed_multiplier = 0.8  # slower speaking rate
        explanation_style = "simple"
        
    return {
        "crop_boosts": crop_boosts,
        "explanation_style": explanation_style,
        "risk_preference": risk_preference,
        "speed_multiplier": speed_multiplier
    }
