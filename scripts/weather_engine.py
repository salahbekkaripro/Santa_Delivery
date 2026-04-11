import json
import os
import random

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
WEATHER_FILE = os.path.join(BASE_DIR, 'core_data', 'weather_status.json')

def get_simulated_weather(weather_file=WEATHER_FILE):
    """Simule la météo de Paris de manière réaliste."""
    scenarios = [
        {"condition": "Clear", "desc": "Ciel dégagé", "factor": 1.0},
        {"condition": "Clouds", "desc": "Nuageux", "factor": 1.0},
        {"condition": "Rain", "desc": "Pluie modérée", "factor": 1.3},
        {"condition": "Drizzle", "desc": "Bruine légère", "factor": 1.3},
        {"condition": "Snow", "desc": "Tempête de neige", "factor": 2.0},
        {"condition": "Thunderstorm", "desc": "Orage violent", "factor": 2.0},
        {"condition": "Mist", "desc": "Brouillard givrant", "factor": 2.0}
    ]
    
    # Choix aléatoire pondéré (plus de chance de beau temps/nuages)
    weights = [30, 30, 15, 10, 5, 5, 5]
    current = random.choices(scenarios, weights=weights, k=1)[0]
    
    # Sauvegarde
    os.makedirs(os.path.dirname(weather_file), exist_ok=True)
    with open(weather_file, 'w', encoding='utf-8') as f:
        json.dump(current, f, indent=4, ensure_ascii=False)
    
    print(f"🌡️ Météo simulée : {current['desc']} (Impact : x{current['factor']})")
    return current

if __name__ == "__main__":
    get_simulated_weather()
