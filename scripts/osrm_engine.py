import pandas as pd
import numpy as np
import requests
import os
import time

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(BASE_DIR, 'core_data', 'livraisons_5eme.csv')
OUTPUT_MATRIX = os.path.join(BASE_DIR, 'core_data', 'live_time_matrix.npy')

def get_osrm_matrix():
    # 1. Chargement des adresses
    if not os.path.exists(DATA_PATH):
        print(f"Erreur : {DATA_PATH} introuvable.")
        return
    
    df = pd.read_csv(DATA_PATH)
    coords = [f"{row['lon']},{row['lat']}" for _, row in df.iterrows()]
    coords_str = ";".join(coords)
    
    # 2. Requête à l'API OSRM (Table service)
    # URL : http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration
    url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}"
    params = {"annotations": "duration"}
    
    print(f"Requête OSRM pour {len(df)} points...")
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "durations" in data:
            matrix = np.array(data["durations"])
            # Sauvegarde
            np.save(OUTPUT_MATRIX, matrix)
            print(f"Succès : Matrice de temps ({matrix.shape}) sauvegardée dans {OUTPUT_MATRIX}")
        else:
            print("Erreur : L'API n'a pas renvoyé de durées.")
            
    except Exception as e:
        print(f"Erreur lors de l'appel OSRM : {e}")

if __name__ == "__main__":
    get_osrm_matrix()
