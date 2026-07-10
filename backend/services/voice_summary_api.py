def generate_voice_summary(
    language: str,
    crop: str,
    location_name: str,
    mandi_price: int,
    risk_level: str,
    irrigation_advice: str,
    fertilizer_advice: str,
    urgent_action: str
) -> str:
    """
    Generates natural-sounding speech summary in the target language (English, Telugu, Hindi).
    Uses simple syntax, spelling out prices and containing natural pauses.
    """
    lang_lower = (language or "English").lower()
    
    # Clean location name to just city/district for verbal flow
    loc_clean = location_name.split(",")[0].strip()
    
    if lang_lower == "telugu":
        # Price to Telugu verbal
        price_ten_k = mandi_price // 1000
        price_hundreds = (mandi_price % 1000) // 100
        price_telugu = f"{price_ten_k} వేల"
        if price_hundreds > 0:
            price_telugu += f" {price_hundreds} వందల"
        price_telugu += " రూపాయలు"
        
        summary = (
            f"రైతు సోదరులకు నమస్కారం. "
            f"మీ పొలానికి అత్యంత అనుకూలమైన పంట {crop}. "
            f"{loc_clean} మార్కెట్ లో మండి ధర క్వింటాలుకు సుమారు {price_telugu}. "
            f"వాతావరణ ముప్పు {risk_level} గా ఉంది. "
            f"నీటి యాజమాన్యం కోసం, {irrigation_advice.split('.')[0]}. "
            f"ఎరువుల కొరకు, {fertilizer_advice.split('.')[0]}. "
            f"ముఖ్యమైన గమనిక, {urgent_action}"
        )
        return summary
        
    elif lang_lower == "hindi":
        # Price to Hindi verbal
        price_ten_k = mandi_price // 1000
        price_hundreds = (mandi_price % 1000) // 100
        price_hindi = f"{price_ten_k} हजार"
        if price_hundreds > 0:
            price_hindi += f" {price_hundreds} सौ"
        price_hindi += " रूपये"
        
        summary = (
            f"किसान भाइयों को नमस्कार। "
            f"आपके खेत के लिए सबसे उपयुक्त फसल {crop} है। "
            f"{loc_clean} मंडी में भाव लगभग {price_hindi} प्रति क्विंटल है। "
            f"मौसम का जोखिम {risk_level} स्तर पर है। "
            f"सिंचाई के लिए सलाह है कि, {irrigation_advice.split('.')[0]}। "
            f"खाद प्रबंधन के लिए, {fertilizer_advice.split('.')[0]}। "
            f"आवश्यक चेतावनी, {urgent_action}"
        )
        return summary
        
    else: # English default
        summary = (
            f"Welcome farmer. "
            f"Based on your profile, the best recommended crop is {crop}. "
            f"The modal mandi price near {loc_clean} is around {mandi_price} rupees per quintal. "
            f"Overall climate risk is {risk_level}. "
            f"For watering, {irrigation_advice.split('.')[0]}. "
            f"For fertilizer, {fertilizer_advice.split('.')[0]}. "
            f"Urgent action required, {urgent_action}"
        )
        return summary
