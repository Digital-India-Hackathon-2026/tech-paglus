import os
import json
from typing import Any
from models.schemas import ApiStatus, FarmRequest, RiskScores
from services.http_client import ApiError, post_json

def get_ai_advisory(
    farm: FarmRequest,
    risk: RiskScores,
    weather: ApiStatus,
    mandi_market: ApiStatus,
    crop_knowledge: ApiStatus,
) -> tuple[list[str], list[str], dict[str, Any]]:
    """
    Calls the external LLM or uses local multilingual fallback rules to generate:
    - farmer_advice: list[str]
    - government_alert: list[str]
    - ai_detailed: dict[str, Any] with the 10 required advisor keys
    """
    ai_url = os.getenv("AI_ADVISORY_API_URL")
    ai_key = os.getenv("AI_ADVISORY_API_KEY")
    ai_model = os.getenv("AI_ADVISORY_MODEL", "llama-3.3-70b-versatile")
    
    if ai_url and ai_key:
        try:
            payload = _build_openai_compatible_payload(
                farm=farm,
                risk=risk,
                weather=weather,
                mandi_market=mandi_market,
                crop_knowledge=crop_knowledge,
                model=ai_model,
            )
            data = post_json(ai_url, payload, {"Authorization": f"Bearer {ai_key}"})
            
            # Extract content from completion response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                parsed_json = _parse_and_validate_ai_json(content)
                if parsed_json:
                    advice_list = [parsed_json["farmer_summary"], parsed_json["crop_action"], parsed_json["risk_warning"]]
                    govt_alert = [parsed_json["weather_action"], parsed_json["technical_summary"]]
                    return advice_list, govt_alert, parsed_json
        except Exception:
            pass  # Fallback to local rules
            
    return _fallback_advisory(farm, risk)

def _build_openai_compatible_payload(
    farm: FarmRequest,
    risk: RiskScores,
    weather: ApiStatus,
    mandi_market: ApiStatus,
    crop_knowledge: ApiStatus,
    model: str,
) -> dict:
    context = {
        "location": farm.location,
        "crop": farm.crop,
        "soil_type": farm.soil_type,
        "season": farm.season,
        "land_type": farm.land_type,
        "irrigation_available": farm.irrigation_available,
        "preferred_language": farm.preferred_language,
        "risk": risk.model_dump(),
        "weather": weather.data,
        "mandi_market": mandi_market.data,
        "crop_knowledge": crop_knowledge.data,
    }
    
    system_prompt = (
        "You are AgriSarthi AI, a professional agricultural advisory agent for Indian farmers.\n"
        "Return ONLY a valid JSON object matching this structure (no conversational text before/after):\n"
        "{\n"
        '  "farmer_summary": "Short 1-2 sentence overview for the farmer in their preferred language.",\n'
        '  "technical_summary": "Technical agronomy description of soil/climate compatibility.",\n'
        '  "voice_summary": "Spoken text that summarizes the main crop, price, and actions clearly.",\n'
        '  "crop_action": "Immediate crop sowing or management steps.",\n'
        '  "weather_action": "Spray safety or drainage precaution based on forecast.",\n'
        '  "mandi_action": "Market price strategy (hold or sell).",\n'
        '  "irrigation_action": "Recommended irrigation cycle.",\n'
        '  "fertilizer_action": "Basal or top dressing application tips.",\n'
        '  "risk_warning": "Warning about climate stress or oversupply risk.",\n'
        '  "next_steps": "Actionable task for the FPO or farmer."\n'
        "}\n"
        f"Preferred Language: {farm.preferred_language or 'English'}. Translate summaries and actions to this language."
    )
    
    return {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
    }

def _parse_and_validate_ai_json(content: str) -> dict[str, str] | None:
    # Trim to locate JSON object bounds
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    json_str = content[start : end + 1]
    
    try:
        parsed = json.loads(json_str)
        required_keys = [
            "farmer_summary", "technical_summary", "voice_summary",
            "crop_action", "weather_action", "mandi_action",
            "irrigation_action", "fertilizer_action", "risk_warning", "next_steps"
        ]
        # Validate keys and inject fallback string if missing
        validated = {}
        for key in required_keys:
            validated[key] = str(parsed.get(key, f"Standard advisory action for {key.replace('_', ' ')}."))
        return validated
    except Exception:
        return None

def _fallback_advisory(farm: FarmRequest, risk: RiskScores) -> tuple[list[str], list[str], dict[str, Any]]:
    # Translate fallback templates
    templates = _language_templates(farm.preferred_language)
    
    farmer_advice = []
    government_alert = []
    
    if risk.flood >= 60:
        farmer_advice.append(templates["flood"])
        government_alert.append(templates["flood_admin"])
        risk_msg = templates["flood"]
    elif risk.drought >= 60:
        farmer_advice.append(templates["drought"])
        government_alert.append(templates["drought_admin"])
        risk_msg = templates["drought"]
    else:
        farmer_advice.append(templates["low"])
        risk_msg = templates["low"]
        
    if risk.heat >= 60:
        farmer_advice.append(templates["heat"])
    if risk.wind >= 60:
        farmer_advice.append(templates["wind"])
        
    loc_state = farm.location.split(",")[-1].strip()
    
    # Spell out the 10 JSON keys for consistent layout structure
    ai_detailed = {
        "farmer_summary": farmer_advice[0],
        "technical_summary": f"Agronomic review shows overall risk index is {risk.overall}/100 with level {risk.level}.",
        "voice_summary": f"Summary for {farm.farmer_name}. Best crop recommended is {farm.crop.title()} in {farm.season} season.",
        "crop_action": f"Verify seed germination rate of {farm.crop} before sowing.",
        "weather_action": "Avoid spraying if rain is expected in next 24 hours.",
        "mandi_action": "Check prices in nearest sub-market yard before selling.",
        "irrigation_action": "Maintain soil moisture. Adjust splits based on rainfall.",
        "fertilizer_action": f"Follow basal fertilizer plan matched for soil type {farm.soil_type}.",
        "risk_warning": risk_msg,
        "next_steps": "Link bank details to PM-KISAN database."
    }
    
    # Translate detailed JSON items if Telugu/Hindi
    lang = (farm.preferred_language or "English").lower()
    if lang == "telugu":
        ai_detailed["technical_summary"] = f"వ్యవసాయ నివేదిక ప్రకారం మీ పొలం ముప్పు సూచిక {risk.overall}/100 గా ఉంది."
        ai_detailed["crop_action"] = f"విత్తే ముందు మొలకల శాతాన్ని పరీక్షించుకోండి."
        ai_detailed["weather_action"] = "వర్షం పడే సూచన ఉంటే పురుగుమందుల పిచికారీ వాయిదా వేయండి."
        ai_detailed["mandi_action"] = "పంటను అమ్మే ముందు సమీప మార్కెట్ యార్డ్ ధరలను సరిచూసుకోండి."
        ai_detailed["irrigation_action"] = "తేమను బట్టి తగినంత నీటి పారుదల ఇవ్వండి."
        ai_detailed["fertilizer_action"] = "పొలానికి సిఫార్సు చేసిన ఎరువులను మాత్రమే వాడండి."
        ai_detailed["next_steps"] = "పీఎం కిసాన్ పథకానికి సంబంధించిన వివరాలు సరిచూసుకోండి."
    elif lang == "hindi":
        ai_detailed["technical_summary"] = f"कृषि रिपोर्ट के अनुसार कुल मौसम जोखिम सूचकांक {risk.overall}/100 है।"
        ai_detailed["crop_action"] = "बुवाई से पहले बीज अंकुरण दर की जांच अवश्य करें।"
        ai_detailed["weather_action"] = "यदि अगले २४ घंटों में बारिश की संभावना हो तो छिड़काव न करें।"
        ai_detailed["mandi_action"] = "फसल बेचने से पहले निकटतम कृषि मंडी के भाव की जानकारी लें।"
        ai_detailed["irrigation_action"] = "खेत में नमी बनाए रखें, आवश्यकतानुसार ही सिंचाई करें।"
        ai_detailed["fertilizer_action"] = "मिट्टी परीक्षण कार्ड के अनुसार संतुलित मात्रा में उर्वरक का उपयोग करें।"
        ai_detailed["next_steps"] = "पीएम किसान सम्मान निधि पोर्टल पर अपना विवरण अपडेट करें।"
        
    return farmer_advice, government_alert, ai_detailed

def _language_templates(language: str) -> dict[str, str]:
    normalized = (language or "English").strip().lower()
    if normalized == "telugu":
        return {
            "flood": "వరద ప్రమాదం ఎక్కువగా ఉంది. నీరు బయటకు వెళ్లే కాలువలు తెరవండి; వర్షం ముందు ఎరువు లేదా స్ప్రే వేయవద్దు.",
            "flood_admin": "నీరు నిలిచే పొలాలను పర్యవేక్షించి, పంట నష్టం నమోదు కోసం రైతులను సిద్ధం చేయండి.",
            "drought": "ఎండ ప్రమాదం ఎక్కువగా ఉంది. మల్చింగ్ చేయండి; అవసరమైన దశలో నీటిపారుదల ఇవ్వండి.",
            "drought_admin": "ఎండ ప్రభావిత గ్రామాలకు నీటి వనరులు మరియు పంట బీమా సహాయం ప్రాధాన్యం ఇవ్వండి.",
            "heat": "వేడి ఎక్కువగా ఉంది. మధ్యాహ్నం స్ప్రే చేయవద్దు; చిన్న మొక్కలను రక్షించండి.",
            "wind": "గాలి వేగం ఎక్కువగా ఉండే అవకాశం ఉంది. బలహీన మొక్కలకు సపోర్ట్ ఇవ్వండి; స్ప్రే వాయిదా వేయండి.",
            "low": "ప్రస్తుత ప్రమాదం తక్కువగా ఉంది. సాధారణ సాగు కొనసాగించండి; వాతావరణ హెచ్చరికలను రోజూ చూడండి.",
        }
    if normalized == "hindi":
        return {
            "flood": "बाढ़ का जोखिम अधिक है। खेत में निकासी बनाइए और बारिश से पहले खाद या स्प्रे न करें.",
            "flood_admin": "जलभराव वाले खेतों की निगरानी करें और फसल-नुकसान रिपोर्टिंग के लिए किसानों को तैयार रखें.",
            "drought": "सूखे का जोखिम अधिक है। मल्चिंग करें और जरूरी अवस्था में सिंचाई दें.",
            "drought_admin": "सूखा प्रभावित गांवों में सिंचाई सहायता और फसल बीमा सूचना को प्राथमिकता दें.",
            "heat": "गर्मी का जोखिम अधिक है। दोपहर में रसायन स्प्रे न करें और छोटे पौधों की रक्षा करें.",
            "wind": "तेज हवा का जोखिम है। कमजोर फसलों को सहारा दें और स्प्रे रोक दें.",
            "low": "अभी जोखिम कम है। सामान्य खेती जारी रखें और मौसम चेतावनी देखते रहें.",
        }
    return {
        "flood": "Flood risk is high. Open drainage channels and avoid fertilizer or pesticide application before rainfall.",
        "flood_admin": "Flood-sensitive farms should be monitored for waterlogging and possible crop-loss reporting.",
        "drought": "Drought risk is high. Schedule irrigation and prefer mulching to reduce soil moisture loss.",
        "drought_admin": "Drought-prone farms may need irrigation support and water-resource planning.",
        "heat": "Heat risk is high. Avoid spraying chemicals during afternoon heat and protect young plants.",
        "wind": "Strong wind risk is high. Provide support to weak crops and avoid pesticide spraying.",
        "low": "Current risk is low. Continue normal farming and monitor updated weather alerts.",
    }
