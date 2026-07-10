from typing import Any

# Agronomic optimal ranges for crop suitability calculation
CROP_SOIL_REQUIREMENTS = {
    "cotton": {"ph_min": 6.0, "ph_max": 8.0, "opt_n": 280, "opt_p": 20, "opt_k": 150},
    "chilli": {"ph_min": 6.0, "ph_max": 7.5, "opt_n": 300, "opt_p": 25, "opt_k": 180},
    "paddy": {"ph_min": 5.5, "ph_max": 7.2, "opt_n": 280, "opt_p": 22, "opt_k": 140},
    "maize": {"ph_min": 5.8, "ph_max": 7.5, "opt_n": 280, "opt_p": 22, "opt_k": 120},
    "groundnut": {"ph_min": 6.0, "ph_max": 7.5, "opt_n": 120, "opt_p": 25, "opt_k": 100},  # Legume, low N demand
    "turmeric": {"ph_min": 5.5, "ph_max": 7.5, "opt_n": 250, "opt_p": 25, "opt_k": 200}
}

def calculate_suitability(crop: str, nutrients: dict[str, Any], soil_type: str) -> dict[str, int]:
    """
    Computes suitability scores (0-100) for a given crop based on soil test values.
    Returns:
    - n_score, p_score, k_score, ph_score, overall_soil_suitability
    """
    crop_lower = crop.lower()
    reqs = CROP_SOIL_REQUIREMENTS.get(crop_lower)
    
    # If requirements not found or nutrients missing, return reasonable defaults
    if not reqs or not nutrients:
        # Default based on raw soil_type
        base_scores = {
            "cotton": {"black": 95, "loamy": 75, "red": 65, "sandy": 40},
            "chilli": {"black": 75, "loamy": 95, "red": 80, "sandy": 50},
            "paddy": {"black": 70, "loamy": 85, "red": 60, "sandy": 30},
            "maize": {"black": 80, "loamy": 90, "red": 75, "sandy": 50},
            "groundnut": {"black": 60, "loamy": 85, "red": 90, "sandy": 75},
            "turmeric": {"black": 70, "loamy": 95, "red": 75, "sandy": 40}
        }
        score = base_scores.get(crop_lower, {}).get(soil_type.lower(), 70)
        return {
            "n_score": 85,
            "p_score": 85,
            "k_score": 85,
            "ph_score": 85,
            "overall_soil_suitability": score
        }
        
    ph = nutrients.get("ph")
    n = nutrients.get("nitrogen")
    p = nutrients.get("phosphorus")
    k = nutrients.get("potassium")
    
    # Calculate pH Score
    if ph is not None:
        if reqs["ph_min"] <= ph <= reqs["ph_max"]:
            ph_score = 100
        else:
            dist = min(abs(ph - reqs["ph_min"]), abs(ph - reqs["ph_max"]))
            ph_score = max(20, int(100 - (dist * 40)))
    else:
        ph_score = 80
        
    # Helper for NPK scores
    def calc_nutrient_score(val, optimal):
        if val is None:
            return 80
        if val >= optimal:
            return 100
        # percentage of optimal
        return max(30, int((val / optimal) * 100))
        
    n_score = calc_nutrient_score(n, reqs["opt_n"])
    p_score = calc_nutrient_score(p, reqs["opt_p"])
    k_score = calc_nutrient_score(k, reqs["opt_k"])
    
    # Soil type compatibilities (adjust base score)
    soil_compat = {
        "cotton": {"black": 1.0, "loamy": 0.8, "red": 0.7, "sandy": 0.4},
        "chilli": {"black": 0.8, "loamy": 1.0, "red": 0.9, "sandy": 0.6},
        "paddy": {"black": 0.9, "loamy": 1.0, "red": 0.7, "sandy": 0.3},
        "maize": {"black": 0.8, "loamy": 1.0, "red": 0.8, "sandy": 0.5},
        "groundnut": {"black": 0.6, "loamy": 0.9, "red": 1.0, "sandy": 0.8},
        "turmeric": {"black": 0.8, "loamy": 1.0, "red": 0.8, "sandy": 0.4}
    }
    
    multiplier = soil_compat.get(crop_lower, {}).get(soil_type.lower(), 0.8)
    
    # Average nutrient scores weighted by soil texture compatibility
    overall = int((ph_score * 0.25 + n_score * 0.25 + p_score * 0.25 + k_score * 0.25) * multiplier)
    
    return {
        "n_score": n_score,
        "p_score": p_score,
        "k_score": k_score,
        "ph_score": ph_score,
        "overall_soil_suitability": max(10, min(100, overall))
    }
