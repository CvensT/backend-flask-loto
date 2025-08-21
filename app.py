import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# === Préparer les chemins ===
BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

# === Importer la fonction métier ===
try:
   from scripts.loto_gen.generateur_ultra_plus import generer_combinaisons_depuis_web
except Exception as e:
    print(f"[BOOT] Échec import generateur_ultra_plus: {e}", flush=True)
    generer_combinaisons_depuis_web = None

# === Initialiser Flask ===
app = Flask(__name__)
CORS(app)  # Autorise les appels cross-origin (frontend)

# === Route de santé pour Render ===
@app.get("/health")
def health():
    return jsonify({"ok": True}), 200

# === Endpoint principal pour générer les combinaisons ===
@app.post("/api/generer")
def generer():
    """
    Reçoit un JSON : {"loterie": "2", "blocs": 2}
    - loterie : "1"=Grande Vie, "2"=Lotto Max, "3"=6/49
    - blocs : nombre de blocs à générer
    """
    if generer_combinaisons_depuis_web is None:
        return jsonify({"ok": False, "error": "Générateur indisponible (import)."}), 500

    try:
        data = request.get_json(force=True) or {}
        loterie = str(data.get("loterie", "2"))
        blocs = int(data.get("blocs", 1))

        # Validation de base
        if loterie not in {"1", "2", "3"}:
            return jsonify({"ok": False, "error": "Loterie invalide."}), 400
        if not (1 <= blocs <= 20):
            return jsonify({"ok": False, "error": "Nombre de blocs invalide (1-20 autorisés)."}), 400

        print(f"[API] Appel générateur — Loterie={loterie} | Blocs={blocs}", flush=True)

        combinaisons = generer_combinaisons_depuis_web(loterie, blocs)

        return jsonify({
            "ok": True,
            "data": combinaisons,
            "echo": {"loterie": loterie, "blocs": blocs},
            "source": "API Flask (local ou Render)"
        })

    except Exception as e:
        print(f"[ERREUR API] {e}", flush=True)
        return jsonify({"ok": False, "error": str(e)}), 500

# === Démarrage local ou Render ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))  # Render injecte PORT
    app.run(host="0.0.0.0", port=port, debug=True)



