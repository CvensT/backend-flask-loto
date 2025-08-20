import os
from collections import Counter
import numpy as np

LOTERIES = {
    "1": {
        "nom": "Grande Vie",
        "csv": "../data/historiques_grande_vie.csv",
        "nombre_numeros": 5,
        "pair_impair_valides": [(3,2), (2,3), (4,1), (1,4)],
        "petit_grand_valides": [(3,2), (2,3), (4,1), (1,4)],
        "groupes_dizaines": 3,
        "fin_identique_max": 2,
        "min_finales": 3,
        "max_par_multi": 4
    },
    "2": {
        "nom": "Lotto Max",
        "csv": "../data/historiques_lotto_max.csv",
        "nombre_numeros": 7,
        "pair_impair_valides": [(4,3), (3,4), (5,2), (2,5)],
        "petit_grand_valides": [(4,3), (3,4), (5,2), (2,5)],
        "groupes_dizaines": 4,
        "fin_identique_max": 3,
        "min_finales": 4,
        "max_par_multi": 5
    },
    "3": {
        "nom": "649",
        "csv": "../data/historiques_649.csv",
        "nombre_numeros": 6,
        "pair_impair_valides": [(3,3), (4,2), (2,4), (5,1), (1,5)],
        "petit_grand_valides": [(3,3), (4,2), (2,4), (5,1), (1,5)],
        "groupes_dizaines": 4,
        "fin_identique_max": 3,
        "min_finales": 4,
        "max_par_multi": 5
    }
}

def test_pair_impair(comb, cfg):
    p = sum(1 for x in comb if x % 2 == 0)
    i = len(comb) - p
    return (p, i) in cfg['pair_impair_valides']

def test_petit_grand(comb, cfg, mediane):
    petit = sum(1 for x in comb if x <= mediane)
    grand = len(comb) - petit
    return (petit, grand) in cfg['petit_grand_valides']

def test_series_max2_sans_quatuor(comb):
    count = 0
    i = 0
    n = len(comb)
    while i < n - 1:
        if comb[i+1] == comb[i] + 1:
            length = 2
            j = i + 1
            while j < n - 1 and comb[j+1] == comb[j] + 1:
                length += 1
                j += 1
            if length > 3:
                return False
            count += 1
            i = j
        else:
            i += 1
    return count <= 2

def test_repartition_dizaines(comb, cfg):
    groupes = [0] * ((max(comb) + 9) // 10)
    for x in comb:
        groupes[(x - 1) // 10] += 1
    return all(c <= cfg['groupes_dizaines'] for c in groupes)

def test_somme(comb, min_s, max_s):
    s = sum(comb)
    return min_s <= s <= max_s

def test_same_ending(comb, cfg):
    endings = Counter(n % 10 for n in comb)
    return all(count <= cfg['fin_identique_max'] for count in endings.values())

def test_diversite_finales(comb, min_finales):
    return len(set(n % 10 for n in comb)) >= min_finales

def test_symboliques(comb, multiplicateurs=range(2, 10), max_par_multi=4):
    for m in multiplicateurs:
        count = sum(1 for n in comb if n % m == 0)
        if count > max_par_multi:
            return False
    return True

def analyse_loterie(cfg):
    path = cfg["csv"]
    nb_numeros = cfg["nombre_numeros"]
    all_combs = []
    sommes = []

    if not os.path.exists(path):
        print(f"Fichier introuvable : {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            try:
                comb = sorted(int(x) for x in parts if x.isdigit())
            except:
                continue
            if len(comb) == nb_numeros:
                all_combs.append(comb)
                sommes.append(sum(comb))

    if not all_combs:
        print(f"Aucune combinaison valide trouvée dans {cfg['nom']}")
        return

    # Calcul de la fourchette interquartile pour somme réaliste
    q1 = np.percentile(sommes, 25)
    q3 = np.percentile(sommes, 75)
    iqr = q3 - q1
    min_s = max(min(sommes), q1 - 1.5 * iqr)
    max_s = min(max(sommes), q3 + 1.5 * iqr)

    mediane = sorted([n for comb in all_combs for n in comb])[len(all_combs)*nb_numeros // 2]

    criteres = [
        ("Pair/Impair", lambda c: test_pair_impair(c, cfg)),
        ("Petit/Grand", lambda c: test_petit_grand(c, cfg, mediane)),
        ("Séries consécutives (max 2, max trio)", test_series_max2_sans_quatuor),
        ("Répartition par dizaines", lambda c: test_repartition_dizaines(c, cfg)),
        ("Somme totale réaliste", lambda c: test_somme(c, min_s, max_s)),
        ("Fins identiques limitées", lambda c: test_same_ending(c, cfg)),
        ("Diversité des finales (unités)", lambda c: test_diversite_finales(c, cfg["min_finales"])),
        ("Multiples (symboliques)", lambda c: test_symboliques(c, max_par_multi=cfg["max_par_multi"])),
    ]

    print(f"\n🔍 Analyse sur {len(all_combs)} tirages de {cfg['nom']} :")
    print(f"🔎 Fourchette somme utilisée : {min_s:.1f} - {max_s:.1f}")
    for nom, func in criteres:
        ok = sum(1 for c in all_combs if func(c))
        pourc = 100 * ok / len(all_combs)
        print(f"- {nom} : {ok} / {len(all_combs)} ({pourc:.2f} %) respectent ce critère")

if __name__ == "__main__":
    print("1️⃣ Grande Vie")
    print("2️⃣ Lotto Max")
    print("3️⃣ 6/49")
    choix = input("Choisissez la loterie à analyser (1, 2 ou 3) : ").strip()
    if choix not in LOTERIES:
        print("Choix invalide.")
    else:
        analyse_loterie(LOTERIES[choix])


