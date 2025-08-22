from flask import Flask, request, jsonify
from flask_cors import CORS
from scripts.loto_gen.generateur_ultra_plus import (
    LOTERIES,
    get_historique_path,
    get_proposes_path,
    generer_par_blocs,
    verifier_criteres,
    charger_historique
)
from collections import Counter

app = Flask(__name__)
CORS(app)

@app.route("/health")
def health():
    return "OK"

@app.route("/api/generer", methods=["POST"])
def generer():
    data = request.get_json()
    loterie_id = data.get("loterie")
    mode = data.get("mode", "Gb")
    nb_blocs = int(data.get("blocs", 1))

    cfg = LOTERIES.get(str(loterie_id))
    if not cfg:
        return jsonify(ok=False, error="Loterie invalide"), 400

    total_combis = nb_blocs * (cfg["par_bloc_base"] + 1)
    combis, _ = generer_par_blocs(cfg, total_combis)
    resultat = [
        {"bloc": bloc, "combinaison": comb, "etoile": is_star}
        for bloc, comb, is_star in combis
    ]
    return jsonify(ok=True, data=resultat, echo={"loterie": loterie_id, "blocs": nb_blocs}, source="API Flask (Render)")

@app.route("/api/verifier", methods=["POST"])
def verifier_combinaison_api():
    data = request.get_json()
    loterie_id = data.get("loterie")
    combinaison = data.get("combinaison")

    cfg = LOTERIES.get(str(loterie_id))
    if not cfg:
        return jsonify(ok=False, error="Loterie invalide."), 400

    if not isinstance(combinaison, list) or not all(isinstance(n, int) for n in combinaison):
        return jsonify(ok=False, error="Format de combinaison invalide."), 400

    resultats = verifier_criteres([combinaison], cfg)
    return jsonify(ok=True, resultats=resultats)

@app.route("/api/verifier-bloc", methods=["POST"])
def verifier_bloc_api():
    data = request.get_json()
    loterie_id = data.get("loterie")
    combinaisons = data.get("combinations")

    cfg = LOTERIES.get(str(loterie_id))
    if not cfg:
        return jsonify(ok=False, error="Loterie invalide."), 400

    if not isinstance(combinaisons, list) or not all(isinstance(c, list) and all(isinstance(n, int) for n in c) for c in combinaisons):
        return jsonify(ok=False, error="Format des combinaisons invalide."), 400

    audits = verifier_criteres(combinaisons, cfg)

    doublons = []
    combi_tuples = [tuple(sorted(c)) for c in combinaisons]
    compteur = Counter(combi_tuples)
    for c, n in compteur.items():
        if n > 1:
            doublons.append(c)

    invalides = [i for i, r in enumerate(audits) if not all(list(r.values())[1:])]

    msg = f"Bloc analysé : {len(doublons)} doublon(s), {len(invalides)} combinaison(s) invalide(s)."
    return jsonify(ok=True, message=msg, doublons=doublons, invalides=invalides, audits=audits)

@app.route("/api/verifier-historique", methods=["POST"])
def verifier_dans_historique_api():
    data = request.get_json()
    loterie_id = data.get("loterie")
    combinaison = data.get("combinaison")

    cfg = LOTERIES.get(str(loterie_id))
    if not cfg:
        return jsonify(ok=False, error="Loterie invalide."), 400

    if not isinstance(combinaison, list) or not all(isinstance(n, int) for n in combinaison):
        return jsonify(ok=False, error="Format de combinaison invalide."), 400

    taille = cfg["nombre_numeros"]
    combi_sorted = tuple(sorted(combinaison))
    path = get_historique_path(cfg)
    historique = charger_historique(path, taille)

    if combi_sorted in historique:
        return jsonify(ok=True, message="✅ Cette combinaison a été tirée dans le passé.")
    else:
        return jsonify(ok=True, message="❌ Cette combinaison n’a jamais été tirée.")

@app.route("/api/historique")
def afficher_historique():
    loterie_id = request.args.get("loterie")
    cfg = LOTERIES.get(str(loterie_id))
    if not cfg:
        return jsonify(ok=False, error="Loterie invalide"), 400

    taille = cfg["nombre_numeros"]
    path = get_historique_path(cfg)
    historique = charger_historique(path, taille)

    data = [list(comb) for comb in sorted(historique)]
    return jsonify(ok=True, data=data)

if __name__ == "__main__":
    app.run(debug=True, port=5050)
