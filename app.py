# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
from pathlib import Path

# === On branche sur TON fichier réel ===
from scripts.loto_gen.generateur_ultra_plus import (
    LOTERIES,
    extraire_tirage,
    generer_combinaisons_depuis_web,
    verifier_criteres,
    get_historique_path,
    charger_historique,
)

app = Flask(__name__)
CORS(app)

# ---------- Petites utilités "neutres" (pas de logique métier doublée) ----------

def _comb_sorted(nums):
    return tuple(sorted(int(x) for x in nums))

def _compute_mediane_from_history(cfg):
    """Calcule la médiane (pour Petit/Grand) en réutilisant tes CSV d'historique."""
    histo_path = Path(get_historique_path(cfg))
    tous = []
    if histo_path.exists():
        # On gère le cas CSV avec entêtes/colonnes (comme dans ton code)
        with histo_path.open(newline='') as f:
            try:
                rdr = csv.DictReader(f)
                has_header = rdr.fieldnames is not None
                if has_header:
                    f.seek(0)
                    rdr = csv.DictReader(f)
                    for row in rdr:
                        if not any(row.values()):
                            continue
                        tir = extraire_tirage(row)
                        if len(tir) == cfg['nombre_numeros']:
                            tous.extend(tir)
            except Exception:
                pass
            # fallback simple: lignes libres
            if not tous:
                f.seek(0)
                for line in f:
                    parts = line.strip().replace(',', ' ').split()
                    nums = [int(x) for x in parts if x.isdigit()]
                    if len(nums) == cfg['nombre_numeros']:
                        tous.extend(nums)

    return (sorted(tous)[len(tous)//2] if tous else 25)

# ---------- Routes ----------

@app.route("/api/generer", methods=["POST"])
def api_generer():
    """
    Corps attendu:
    { "loterie": "1|2|3", "mode": "Gb", "blocs": 1 }
    """
    body = request.get_json(force=True, silent=True) or {}
    loterie = str(body.get("loterie", "2"))
    blocs = int(body.get("blocs", 1))

    try:
        data = generer_combinaisons_depuis_web(loterie, blocs)
        return jsonify({"ok": True, "data": data, "source": "API Flask (Render)"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500

@app.route("/api/verifier", methods=["POST"])
def api_verifier():
    """
    Vérifie si une combinaison est présente dans l'historique.
    Corps attendu:
    { "loterie": "1|2|3", "combinaison": [..] }
    Réponse:
    { "ok": true, "data": { "existe": bool, "criteres": {...} } }
    """
    body = request.get_json(force=True, silent=True) or {}
    loterie = str(body.get("loterie", "2"))
    combinaison = body.get("combinaison", [])

    cfg = LOTERIES.get(loterie)
    if not cfg:
        return jsonify({"ok": False, "error": "Loterie invalide"}), 400
    if not isinstance(combinaison, list) or not combinaison:
        return jsonify({"ok": False, "error": "combinaison manquante"}), 400

    try:
        taille = cfg["nombre_numeros"]
        histo_path = get_historique_path(cfg)
        histo_set = charger_historique(histo_path, taille)

        target = _comb_sorted(combinaison)
        existe = (target in histo_set)

        # On renvoie aussi le détail de tes critères réels (via verifier_criteres)
        mediane = _compute_mediane_from_history(cfg)
        audits = verifier_criteres(list(target), cfg, mediane)  # ta fonction
        detail = audits[0] if audits else {}

        return jsonify({"ok": True, "data": {"existe": bool(existe), "criteres": detail}}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500

@app.route("/api/verifier-bloc", methods=["POST"])
def api_verifier_bloc():
    """
    Vérifie un BLOC: toutes les combinaisons respectent les critères +
    aucun doublon de NUMÉRO dans la BASE (sauf étoile autorisée à réutiliser).
    Corps attendu:
    {
      "loterie": "1|2|3",
      "bloc": [[...], ...],          # longueur = par_bloc_base + 1
      "etoileIndex": <int>           # index 0-based, souvent dernier
    }
    Réponse:
    { "ok": true, "data": { "valide": bool, "erreurs": [...], "details": {...} } }
    """
    body = request.get_json(force=True, silent=True) or {}
    loterie = str(body.get("loterie", "2"))
    bloc = body.get("bloc", [])
    etoile_index = body.get("etoileIndex", None)

    cfg = LOTERIES.get(loterie)
    if not cfg:
        return jsonify({"ok": False, "error": "Loterie invalide"}), 400
    if not isinstance(bloc, list) or not bloc:
        return jsonify({"ok": False, "error": "bloc manquant"}), 400

    try:
        # Normalise + paramètres
        bloc_norm = [list(map(int, c)) for c in bloc]
        par_bloc_base = cfg["par_bloc_base"]
        attendu = par_bloc_base + 1
        if len(bloc_norm) != attendu:
            return jsonify({"ok": False, "error": f"Le bloc doit contenir exactement {attendu} combinaisons ({par_bloc_base} base + 1 étoile)."}), 400

        if etoile_index is None:
            etoile_index = len(bloc_norm) - 1  # par convention, la dernière

        # 1) Critères réels (ta fonction) sur TOUTES les combinaisons
        mediane = _compute_mediane_from_history(cfg)
        audits = verifier_criteres(bloc_norm, cfg, mediane)  # ta fonction
        erreurs = []
        for i, a in enumerate(audits):
            # Si au moins un des tests est False -> erreur
            if not all(bool(v) for k, v in a.items() if k not in ("Combinaison",)):
                erreurs.append(f"Combinaison {i+1} ne respecte pas tous les critères")

        # 2) Doublons de NUMÉRO dans la BASE (interdits) — l’étoile peut réutiliser
        base_idx = [i for i in range(len(bloc_norm)) if i != etoile_index]
        vus = {}
        for i in base_idx:
            for n in bloc_norm[i]:
                vus[n] = vus.get(n, 0) + 1
        doublons_numeros = sorted([n for n, c in vus.items() if c > 1])
        if doublons_numeros:
            erreurs.append(f"Doublons de numéros détectés dans la base: {doublons_numeros}")

        # 3) Détail utile: on renvoie aussi l’audit détaillé
        ok = (len(erreurs) == 0)
        return jsonify({"ok": True, "data": {"valide": ok, "erreurs": erreurs, "details": audits}}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500

@app.route("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(5050))
