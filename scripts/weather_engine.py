import json
import os
import random
import requests
import osmnx as ox

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
WEATHER_FILE = os.path.join(BASE_DIR, 'core_data', 'weather_status.json')

WEATHER_SCENARIOS = {
    "Clear": {"condition": "Clear", "desc": "Ciel dégagé", "factor": 1.0},
    "Clouds": {"condition": "Clouds", "desc": "Nuageux", "factor": 1.0},
    "Rain": {"condition": "Rain", "desc": "Pluie modérée", "factor": 1.3},
    "Drizzle": {"condition": "Drizzle", "desc": "Bruine légère", "factor": 1.3},
    "Snow": {"condition": "Snow", "desc": "Tempête de neige", "factor": 2.0},
    "Thunderstorm": {"condition": "Thunderstorm", "desc": "Orage violent", "factor": 2.0},
    "Mist": {"condition": "Mist", "desc": "Brouillard givrant", "factor": 2.0}
}

def get_simulated_weather(weather_file=WEATHER_FILE):
    """Simule la météo de Paris de manière réaliste."""
    scenarios = list(WEATHER_SCENARIOS.values())
    # Choix aléatoire pondéré (plus de chance de beau temps/nuages)
    weights = [30, 30, 15, 10, 5, 5, 5]
    current = random.choices(scenarios, weights=weights, k=1)[0]
    
    _save_weather(current, weather_file)
    print(f"🌡️ Météo simulée : {current['desc']} (Impact : x{current['factor']})")
    return current

def get_real_weather(location_name, weather_file=WEATHER_FILE):
    """Récupère la météo réelle via l'API Open-Meteo (Gratuit, pas de clé)."""
    try:
        print(f"🌍 Récupération météo réelle pour : {location_name}...")
        lat, lon = ox.geocode(location_name)
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current_weather", {})
        code = current.get("weathercode", 0)
        temp = current.get("temperature", 15)
        
        # Mapping WMO Codes (simplifié)
        if code == 0: key = "Clear"
        elif code in [1, 2, 3]: key = "Clouds"
        elif code in [45, 48]: key = "Mist"
        elif code in [51, 53, 55]: key = "Drizzle"
        elif code in [61, 63, 65, 80, 81, 82]: key = "Rain"
        elif code in [71, 73, 75, 85, 86]: key = "Snow"
        elif code in [95, 96, 99]: key = "Thunderstorm"
        else: key = "Clear"
        
        weather = dict(WEATHER_SCENARIOS[key])
        weather["desc"] = f"{weather['desc']} ({temp}°C)"
        weather["real_temp"] = temp
        
        _save_weather(weather, weather_file)
        print(f"🌡️ Météo réelle : {weather['desc']} (Impact : x{weather['factor']})")
        return weather
        
    except Exception as e:
        print(f"⚠️ Échec météo réelle ({e}), repli sur simulation.")
        return get_simulated_weather(weather_file)

def _save_weather(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    get_real_weather("Paris")
