import os
import sys
import csv
import json
import random
import unicodedata
from collections import Counter
from math import ceil
from pathlib import Path

# --- Utilitaire pour extraire une ligne de tirage (si CSV colonnes) ---
def extraire_tirage(row):
    return sorted(int(v) for v in row.values() if v and str(v).isdigit())

# === Paramètres des loteries (AVEC fourchettes de somme fixes) ===
LOTERIES = {
    "1": {
        "nom": "Grande Vie",
        "historique": "historiques_grande_vie.csv",
        "nombre_numeros": 5,
        "plage_numeros": (1, 49),
        "pair_impair_valides": [(3,2), (2,3), (4,1), (1,4)],
        "petit_grand_valides": [(3,2), (2,3), (4,1), (1,4)],
        "groupes_dizaines": 3,
        "fin_identique_max": 2,
        "min_finales": 3,
        "max_par_multi": 4,
        "somme_min": 80,
        "somme_max": 179,
        "par_bloc_base": 9,
        "reutilises_dans_etoile": 1
    },
    "2": {
        "nom": "Lotto Max",
        "historique": "historiques_lotto_max.csv",
        "nombre_numeros": 7,
        "plage_numeros": (1, 50),
        "pair_impair_valides": [(4,3), (3,4), (5,2), (2,5)],
        "petit_grand_valides": [(4,3), (3,4), (5,2), (2,5)],
        "groupes_dizaines": 4,
        "fin_identique_max": 3,
        "min_finales": 4,
        "max_par_multi": 5,
        "somme_min": 140,
        "somme_max": 219,
        "par_bloc_base": 7,
        "reutilises_dans_etoile": 6
    },
    "3": {
        "nom": "649",
        "historique": "historiques_649.csv",
        "nombre_numeros": 6,
        "plage_numeros": (1, 49),
        "pair_impair_valides": [(3,3), (4,2), (2,4), (5,1)],
        "petit_grand_valides": [(3,3), (4,2), (2,4), (5,1)],
        "groupes_dizaines": 4,
        "fin_identique_max": 3,
        "min_finales": 4,
        "max_par_multi": 5,
        "somme_min": 100,
        "somme_max": 199,
        "par_bloc_base": 8,
        "reutilises_dans_etoile": 5
    }
}

# --- Dossiers de données (prod-safe Render + compat lecture) ---
import os, unicodedata
from pathlib import Path

THIS_FILE = Path(__file__).resolve()

# Remonte jusqu’à la racine du projet (celle qui contient normalement 'scripts' ou '.git')
PROJECT_ROOT = THIS_FILE
for _ in range(6):
    if (PROJECT_ROOT / "scripts").is_dir() or (PROJECT_ROOT / ".git").exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent

# 1) DATA_DIR prioritaire via env (ex: /data sur Render si disque persistant monté)
DATA_DIR_ROOT = Path(os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
# 2) Ancien emplacement toléré en LECTURE
DATA_DIR_SCRIPTS = (PROJECT_ROOT / "scripts" / "data").resolve()

# Création du dossier d’écriture si possible
try:
    DATA_DIR_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    # Si le FS est read-only (ex: Vercel), on laisse passer : l’écriture sera gérée côté backend
    pass

def _slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower().strip().replace(' ', '_')
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    return ''.join(ch for ch in s if ch in allowed)

def get_historique_path(cfg) -> str:
    """
    Lecture : on cherche d'abord dans DATA_DIR_ROOT, sinon fallback scripts/data
    """
    name = cfg['historique']
    p1 = DATA_DIR_ROOT / name
    if p1.exists():
        return str(p1)
    p2 = DATA_DIR_SCRIPTS / name
    return str(p2) if p2.exists() else str(p1)  # défaut: racine

def get_proposes_path(cfg) -> str:
    """
    Écriture : toujours dans DATA_DIR_ROOT (configurable par $DATA_DIR)
    """
    slug = _slugify(cfg['nom'])
    return str(DATA_DIR_ROOT / f"proposes_lot_{slug}.csv")

# --- Chargements (historique SANS calcul de sommes) ---
def charger_historique(path, n):
    historique = set()
    if not os.path.exists(path):
        return historique
    # Lecture tolérante: ligne libre OU CSV
    with open(path, 'r', encoding='utf-8', newline='') as f:
        sample = f.read(2048)
        f.seek(0)
        sniffed_has_header = (',' in sample and '\n' in sample and any(h.isalpha() for h in sample.split('\n',1)[0]))
        if sniffed_has_header:
            rdr = csv.DictReader(f)
            for row in rdr:
                if not any(row.values()):
                    continue
                tir = extraire_tirage(row)
                if len(tir) == n:
                    historique.add(tuple(tir))
        else:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.replace(',', ' ').replace(';', ' ').split()
                nums = [int(x) for x in parts if x.isdigit()]
                if len(nums) == n:
                    historique.add(tuple(sorted(nums)))
    return historique

def charger_proposes(path, n):
    proposes = set()
    if os.path.exists(path):
        with open(path, newline='') as f:
            for line in f:
                nums = [int(x) for x in line.replace(',', ' ').replace(';', ' ').split() if x.strip().isdigit()]
                if len(nums) == n:
                    proposes.add(tuple(sorted(nums)))
    return proposes

def charger_proposes_avec_types(path, n):
    """Retourne (set_base, set_etoile) en lisant les lignes; '*' en tête = étoile."""
    base, star = set(), set()
    if not os.path.exists(path):
        return base, star
    with open(path, newline='') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            tokens = raw.replace(',', ' ').replace(';', ' ').split()
            is_star = False
            if tokens and not tokens[0].isdigit():
                is_star = True
                tokens = tokens[1:]
            nums = [int(x) for x in tokens if x.isdigit()]
            if len(nums) == n:
                t = tuple(sorted(nums))
                (star if is_star else base).add(t)
    return base, star

# --- Critères ---
def test_pair_impair(comb, cfg):
    p = sum(1 for x in comb if x % 2 == 0)
    i = len(comb) - p
    return (p, i) in cfg['pair_impair_valides']

def test_petit_grand(comb, cfg, mediane):
    petit = sum(1 for x in comb if x <= mediane)
    grand = len(comb) - petit
    return (petit, grand) in cfg['petit_grand_valides']

def test_series_max2_sans_quatuor(comb):
    # max 2 séries, aucune série >= 4
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
    groups = [0] * ((cfg['plage_numeros'][1] + 9) // 10)
    for x in comb:
        groups[(x - 1) // 10] += 1
    return all(c <= cfg['groupes_dizaines'] for c in groups)

def test_somme(comb, min_s, max_s):
    s = sum(comb)
    return min_s <= s <= max_s

def test_same_ending(comb, cfg):
    endings = Counter(n % 10 for n in comb)
    return all(count <= cfg['fin_identique_max'] for count in endings.values())

def test_diversite_finales(comb, cfg):
    return len(set(n % 10 for n in comb)) >= cfg['min_finales']

def test_symboliques(comb, multiplicateurs=range(2, 10), max_par_multi=4):
    for m in multiplicateurs:
        count = sum(1 for n in comb if n % m == 0)
        if count > max_par_multi:
            return False
    return True

def verifier_criteres(combinaisons, cfg, mediane=25):
    # Utilise les bornes fixes depuis cfg
    somme_min = cfg["somme_min"]
    somme_max = cfg["somme_max"]

    if not combinaisons:
        return []
    if isinstance(combinaisons[0], int):
        combinaisons = [combinaisons]
    results = []
    for comb in combinaisons:
        comb = tuple(sorted(comb))
        res = {
            "Combinaison": comb,
            "Pair/Impair": test_pair_impair(comb, cfg),
            "Petit/Grand": test_petit_grand(comb, cfg, mediane),
            "Séries": test_series_max2_sans_quatuor(comb),
            "Dizaines": test_repartition_dizaines(comb, cfg),
            "Somme": test_somme(comb, somme_min, somme_max),
            "Fin identique": test_same_ending(comb, cfg),
            "Diversité finales": test_diversite_finales(comb, cfg),
            "Symboliques": test_symboliques(comb, range(2, 10), cfg['max_par_multi']),
        }
        results.append(res)
    return results

# --- Outils pour Vb ---
def etoile_est_sous_ensemble_de_base(base, star):
    used = set(x for c in base for x in c)
    return all(x in used for x in star)

# --- Génération par blocs couvrants + étoile (utilise fourchettes fixes cfg) ---
def generer_par_blocs(cfg, nb_total):
    taille = cfg["nombre_numeros"]
    debut, fin = cfg["plage_numeros"]
    total_numeros = set(range(debut, fin + 1))

    par_bloc_base = cfg["par_bloc_base"]
    reutilises_dans_etoile = cfg["reutilises_dans_etoile"]
    somme_min, somme_max = cfg["somme_min"], cfg["somme_max"]

    histo_path = get_historique_path(cfg)
    prop_path = get_proposes_path(cfg)

    historique = charger_historique(histo_path, taille)
    propositions = charger_proposes(prop_path, taille)

    # Médiane dynamique (à partir de l'historique) pour Petit/Grand
    tous = []
    if os.path.exists(histo_path):
        with open(histo_path, newline='') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                tir = [int(x) for x in parts if x.isdigit()]
                if len(tir) == taille:
                    tous.extend(tir)
    mediane = sorted(tous)[len(tous)//2] if tous else 25

    res = []
    combis_deja = set()
    par_bloc_total = par_bloc_base + 1
    nb_blocs = ceil(nb_total / par_bloc_total)

    for bloc_id in range(1, nb_blocs + 1):
        for essai_bloc in range(800):
            base = []
            dispo = list(range(debut, fin + 1))
            random.shuffle(dispo)
            ok_bloc = True

            # Générer la base
            for i in range(par_bloc_base):
                success_this = False
                for _ in range(400):
                    if len(dispo) < taille:
                        success_this = False
                        break
                    cand = tuple(sorted(random.sample(dispo, taille)))

                    if (
                        cand in historique
                        or cand in propositions
                        or cand in combis_deja
                        or cand in base
                        or not test_pair_impair(cand, cfg)
                        or not test_petit_grand(cand, cfg, mediane)
                        or not test_series_max2_sans_quatuor(cand)
                        or not test_repartition_dizaines(cand, cfg)
                        or not test_same_ending(cand, cfg)
                        or not test_diversite_finales(cand, cfg)
                        or not test_symboliques(cand, range(2, 10), cfg['max_par_multi'])
                        or not test_somme(cand, somme_min, somme_max)
                    ):
                        continue

                    base.append(cand)
                    for x in cand:
                        if x in dispo:
                            dispo.remove(x)
                    success_this = True
                    break
                if not success_this:
                    ok_bloc = False
                    break

            if not ok_bloc:
                continue

            # Construire l'étoile
            used_base_nums = set(x for comb in base for x in comb)
            restants = list(total_numeros - used_base_nums)
            random.shuffle(restants)

            taille_etoile = taille
            nb_restants = len(restants)
            nb_reutilises = taille_etoile - nb_restants
            if nb_reutilises < reutilises_dans_etoile:
                nb_reutilises = reutilises_dans_etoile
                nb_restants = taille_etoile - nb_reutilises
                if nb_restants > len(restants):
                    continue

            reutilises_pool = list(used_base_nums)
            random.shuffle(reutilises_pool)

            etoile_reutilises = reutilises_pool[:nb_reutilises]
            etoile_restants = restants[:nb_restants]

            etoile = tuple(sorted(etoile_reutilises + etoile_restants))

            # Validation étoile
            if (
                etoile in historique
                or etoile in propositions
                or etoile in combis_deja
                or etoile in base
                or not test_pair_impair(etoile, cfg)
                or not test_petit_grand(etoile, cfg, mediane)
                or not test_series_max2_sans_quatuor(etoile)
                or not test_repartition_dizaines(etoile, cfg)
                or not test_same_ending(etoile, cfg)
                or not test_diversite_finales(etoile, cfg)
                or not test_symboliques(etoile, range(2, 10), cfg['max_par_multi'])
                or not test_somme(etoile, somme_min, somme_max)
            ):
                continue

            for c in base:
                res.append((bloc_id, c, False))
                combis_deja.add(c)
                if len(res) >= nb_total:
                    break
            if len(res) >= nb_total:
                break

            res.append((bloc_id, etoile, True))
            combis_deja.add(etoile)
            print(f"Bloc {bloc_id} généré ({len(base)}/{par_bloc_base}) + étoile ★")
            break
        else:
            print(f"Bloc {bloc_id} : échec après de multiples tentatives.")
            break

        if len(res) >= nb_total:
            break

    return res[:nb_total], prop_path

# --- I/O console ---
def lire_combinaisons_attendues(taille_comb):
    while True:
        lines = []
        print(f"\nCollez ou tapez vos combinaisons ({taille_comb} chiffres chacune, espaces ou virgules, ligne vide pour terminer) :")
        while True:
            l = input()
            if not l.strip():
                break
            try:
                nettoye = ' '.join(l.replace(',', ' ').split())
                nums = [int(x) for x in nettoye.split()]
                if len(nums) != taille_comb:
                    print(f"❌ Il faut {taille_comb} chiffres par combinaison. Erreur dans la ligne : '{l}'")
                    continue
                lines.append(nums)
            except Exception as e:
                print(f"❌ Mauvais format dans la ligne : '{l}'. Détail : {e}")
                continue
        if lines:
            return lines
        else:
            print("Aucune combinaison saisie. Veuillez recommencer.")

def _tick(b):
    return '✔' if b else '✗'

def _fmt_comb(comb):
    return ' '.join(f"{x:02d}" for x in comb)

def afficher_blocs(combis, avec_bloc=True):
    courant = None
    for bloc_id, comb, is_star in combis:
        if avec_bloc and bloc_id != courant:
            print(f"\nBloc {bloc_id} :")
            courant = bloc_id
        line = ' '.join(str(x) for x in comb)
        print(f"{line}  ★" if is_star else line)

def afficher_table_verif(lignes):
    headers = ["No", "Combinaison", "Pair/Impair", "Petit/Grand", "Séries", "Dizaines", "Fin id.", "Diversité", "Symboliques", "Somme"]
    rows = []
    for i, r in enumerate(lignes, 1):
        somme_val = sum(r["Combinaison"])
        rows.append([
            f"{i:02d}.",
            _fmt_comb(r["Combinaison"]),
            _tick(r["Pair/Impair"]),
            _tick(r["Petit/Grand"]),
            _tick(r["Séries"]),
            _tick(r["Dizaines"]),
            _tick(r["Fin identique"]),
            _tick(r["Diversité finales"]),
            _tick(r["Symboliques"]),
            f"{_tick(r['Somme'])} ({somme_val})"
        ])

    widths = [max(len(h), *(len(row[c]) for row in rows)) for c, h in enumerate(headers)]

    def pr_line(cols):
        print(" | ".join(s.ljust(widths[i]) for i, s in enumerate(cols)))

    pr_line(headers)
    print("-" * (sum(widths) + 3 * (len(headers) - 1)))
    for row in rows:
        pr_line(row)

def choix_loterie():
    while True:
        print("\n1️⃣ Grande Vie\n2️⃣ Lotto Max\n3️⃣ Lotto 6/49")
        choix = input("👉 Choisissez la loterie (1, 2 ou 3) : ").strip()
        if choix in LOTERIES:
            return LOTERIES[choix]
        print("❌ Choix invalide. Réessayez.")

def saisie_nb_blocs(cfg_nom):
    if cfg_nom == "Grande Vie":
        par_bloc_base = 9
    elif cfg_nom == "Lotto Max":
        par_bloc_base = 7
    elif cfg_nom == "649":
        par_bloc_base = 8
    else:
        raise ValueError("Loterie inconnue")

    while True:
        try:
            nb_blocs = int(input("👉 Combien de blocs voulez-vous ? "))
            if nb_blocs > 0:
                return nb_blocs, par_bloc_base
        except Exception:
            pass
        print("❌ Nombre invalide. Réessayez.")

# --- Menu principal (GB / V / Vb) ---
def menu_principal():
    while True:
        print("\n🎯 Menu principal")
        print("(Gb) Génération par blocs couvrants (+ étoile)")
        print("(V)  Vérifier si combinaison existe")
        print("(Vb) Vérifier couverture de blocs (format forcé base+étoile)")
        action = input("👉 Que voulez-vous faire ? [Gb/V/Vb] : ").strip().lower()
        if action not in ('gb', 'v', 'vb'):
            print("❌ Option invalide. Réessayez.")
            continue

        # Choix de la loterie
        cfg = choix_loterie()
        taille_comb = cfg['nombre_numeros']
        histo_path = get_historique_path(cfg)
        prop_path = get_proposes_path(cfg)
        somme_min, somme_max = cfg["somme_min"], cfg["somme_max"]

        # ✅ Confirmation juste après le choix de la loterie
        print(f"\n🧩 Loterie sélectionnée : {cfg['nom']} — taille {taille_comb}, plage {cfg['plage_numeros'][0]}–{cfg['plage_numeros'][1]}")
        print(f"➕ Fourchette de somme : {somme_min} – {somme_max}")
        if action in ('gb', 'vb'):
            print(f"🧱 Par bloc (base) : {cfg['par_bloc_base']}  |  Réutilisés dans étoile : {cfg['reutilises_dans_etoile']}")
        check_lot = input("Appuyez Entrée pour continuer, ou tapez M pour revenir au menu principal : ").strip().lower()
        if check_lot == 'm':
            continue

        if action == 'v':
            # Pré-menu V
            pre_cmd = input("\nAppuyez Entrée pour commencer la vérification, ou tapez M pour revenir au menu principal : ").strip().lower()
            if pre_cmd == 'm':
                continue

            while True:
                lines = lire_combinaisons_attendues(taille_comb)

                # Chargements
                historique = charger_historique(histo_path, taille_comb)
                proposes = charger_proposes(prop_path, taille_comb)

                # Médiane pour Petit/Grand (si historique dispo)
                tous = []
                if os.path.exists(histo_path):
                    with open(histo_path, newline='') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            parts = line.split()
                            tir = [int(x) for x in parts if x.isdigit()]
                            if len(tir) == taille_comb:
                                tous.extend(tir)
                mediane = sorted(tous)[len(tous) // 2] if tous else 25

                audits = verifier_criteres(lines, cfg, mediane)
                afficher_table_verif(audits)
                print(f"\nFourchette somme appliquée : {somme_min} - {somme_max}")

                print("\nStatut :")
                for nums in lines:
                    combinaison = tuple(sorted(nums))
                    aff = _fmt_comb(combinaison)
                    in_histo = combinaison in historique
                    in_propose = combinaison in proposes

                    if in_histo and in_propose:
                        print(f"📂📝 {aff} : dans historique ET proposés")
                    elif in_histo:
                        print(f"📂 {aff} : déjà tirée (historique)")
                    elif in_propose:
                        print(f"📝 {aff} : déjà proposée")
                    else:
                        print(f"✅ {aff} : nouvelle combinaison")

                relancer = input("\n🔄 Vérifier d'autres combinaisons ? [O/N] : ").strip().lower()
                if relancer != 'o':
                    break

        elif action == 'vb':
            # Pré-menu Vb
            pre_cmd = input("\nAppuyez Entrée pour commencer la vérification blocs, ou tapez M pour revenir au menu principal : ").strip().lower()
            if pre_cmd == 'm':
                continue

            par_bloc_base = cfg["par_bloc_base"]
            bloc_total = par_bloc_base + 1

            # Médiane (si CSV avec colonnes)
            tous = []
            if os.path.exists(histo_path):
                with open(histo_path, newline='') as f:
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
                                if len(tir) == taille_comb:
                                    tous.extend(tir)
                    except Exception:
                        pass
            mediane = sorted(tous)[len(tous) // 2] if tous else 25

            print(f"\nℹ️ Format requis par bloc: {par_bloc_base} combinaisons de base + 1 étoile (dernière) → total {bloc_total}.")
            print(f"ℹ️ Fourchette somme appliquée : {somme_min} - {somme_max}")

            while True:
                print(f"\nCollez vos combinaisons (groupées par blocs de {bloc_total} lignes, la dernière étant l'étoile).")
                print("➡️ Ligne vide pour terminer l'entrée. Tapez 'M' à tout moment pour revenir au menu.")
                lines = []
                retour_menu = False

                while True:
                    l = input()
                    s = l.strip()
                    if not s:
                        break
                    if s.lower() in {'m', 'menu', 'q', 'quit'}:
                        retour_menu = True
                        break
                    nums = [int(x) for x in l.replace(',', ' ').split() if x.strip().isdigit()]
                    if len(nums) != taille_comb:
                        print(f"❌ Ligne invalide ({len(nums)}/{taille_comb} chiffres) : {l}")
                        continue
                    lines.append(nums)

                if retour_menu:
                    break

                if not lines:
                    print("Aucune combinaison fournie.")
                    break

                if len(lines) % bloc_total != 0:
                    print(f"❌ Nombre de lignes ({len(lines)}) non multiple de {bloc_total}. Entrée ignorée.")
                    continue

                for bloc_idx in range(0, len(lines), bloc_total):
                    bloc = lines[bloc_idx:bloc_idx + bloc_total]
                    base = bloc[:par_bloc_base]
                    star = bloc[-1]

                    print(f"\nBloc {1 + bloc_idx // bloc_total} :")

                    audits = verifier_criteres(base + [tuple(sorted(star))], cfg, mediane)

                    headers = ["No", "Combinaison", "Pair/Impair", "Petit/Grand", "Séries", "Dizaines", "Fin id.",
                               "Diversité", "Symboliques", f"Somme : {somme_min} - {somme_max}"]
                    rows = []
                    for i, r in enumerate(audits, 1):
                        somme_val = sum(r["Combinaison"])
                        rows.append([
                            f"{i:02d}.",
                            _fmt_comb(r["Combinaison"]),
                            _tick(r["Pair/Impair"]),
                            _tick(r["Petit/Grand"]),
                            _tick(r["Séries"]),
                            _tick(r["Dizaines"]),
                            _tick(r["Fin identique"]),
                            _tick(r["Diversité finales"]),
                            _tick(r["Symboliques"]),
                            f"{_tick(r['Somme'])} ({somme_val})"
                        ])

                    widths = [max(len(h), *(len(row[c]) for row in rows)) for c, h in enumerate(headers)]
                    def pr_line(cols):
                        print(" | ".join(s.ljust(widths[i]) for i, s in enumerate(cols)))

                    pr_line(headers)
                    print("-" * (sum(widths) + 3 * (len(headers) - 1)))
                    for row in rows:
                        pr_line(row)

                    # Analyse couverture/doublons
                    flat_base = [x for comb in base for x in comb]
                    compteur_base = Counter(flat_base)
                    doublons_base = sorted([num for num, cnt in compteur_base.items() if cnt > 1])

                    set_base = set(flat_base)
                    total_numeros = set(range(cfg['plage_numeros'][0], cfg['plage_numeros'][1] + 1))
                    restants_attendus = total_numeros - set_base
                    set_star = set(star)
                    reutilises_etoile = sorted(set_star.intersection(set_base))
                    restants_etoile = sorted(set_star.difference(set_base))

                    if doublons_base:
                        print(f"\n🚨 Doublons détectés dans les combinaisons de base : {doublons_base}")
                    else:
                        print("\n👍 Aucun doublon détecté dans les combinaisons de base.")

                    print(f"\n🔄 Numéros réutilisés dans la combinaison étoile : {reutilises_etoile}")
                    print(f"⚠️ Numéros nouveaux (restants) dans la combinaison étoile : {restants_etoile}")

                    expected_star_set = set_base.union(restants_attendus)
                    if set_star.issubset(expected_star_set):
                        print("✅ Étoile conforme : composée des numéros de base + restants attendus.")
                    else:
                        print("🚨 Étoile NON conforme : contient des numéros hors de la base et des restants attendus.")

                relancer = input("🔄 Vérifier d'autres blocs ? [O/N] : ").strip().lower()
                if relancer != 'o':
                    break

        elif action == 'gb':
            # Pré-menu Gb
            pre_cmd = input("\nAppuyez Entrée pour commencer la génération, ou tapez M pour revenir au menu principal : ").strip().lower()
            if pre_cmd == 'm':
                continue

            while True:
                nb_blocs, par_bloc_base = saisie_nb_blocs(cfg['nom'])
                total_combis = nb_blocs * (par_bloc_base + 1)

                combis, path = generer_par_blocs(cfg, total_combis)
                afficher_blocs(combis, avec_bloc=True)

                # Enregistrer les propositions (créera le fichier si absent)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'a', newline='') as f:
                    writer = csv.writer(f, delimiter=' ')
                    for _bloc_id, c, is_star in combis:
                        row = (['*'] + list(c)) if is_star else list(c)
                        writer.writerow(row)
                print(f"\n📁 Enregistrées dans : {path}")

                encore = input("\n🔁 Générer encore ? [O/N] : ").strip().lower()
                if encore != 'o':
                    break

        # Retour au menu principal ?
        relancer_menu = input("\n🔄 Revenir au menu principal ? [O/N] : ").strip().lower()
        if relancer_menu != 'o':
            print("À bientôt !")
            break

# --- API simple pour le backend / exécution non-interactive ---
def generer_combinaisons_depuis_web(loterie_id: str, nb_blocs: int):
    from .generateur_ultra_plus import generer_par_blocs, LOTERIES

    cfg = LOTERIES.get(loterie_id)
    if not cfg:
        raise ValueError("Loterie invalide")

    total_combis = nb_blocs * (cfg["par_bloc_base"] + 1)

    combis, _ = generer_par_blocs(cfg, total_combis)

    resultat = [
        {
            "bloc": bloc,
            "combinaison": comb,
            "etoile": is_star
        }
        for bloc, comb, is_star in combis
    ]
    return resultat


# --- Entrée principale ---
if __name__ == "__main__":
    # Modes:
    #  - Interactif:          python generateur_ultra_plus.py
    #  - Non-interactif API:  python generateur_ultra_plus.py <loterie_id> <mode> <nb_blocs>
    #
    # Ex: python generateur_ultra_plus.py 2 Gn 1
    if len(sys.argv) >= 4:
        loterie_id = sys.argv[1]
        mode = sys.argv[2]
        try:
            nb_blocs = int(sys.argv[3])
        except ValueError:
            print(json.dumps({"ok": False, "error": "nb_blocs doit être un entier"}))
            sys.exit(2)

        data = generer_combinaisons_depuis_web(loterie_id, nb_blocs, mode)
        # Sortie JSON propre pour le backend
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        sys.exit(0)
    else:
        # Interactif (menu)
        menu_principal()
    if __name__ == "__main__": menu_principal()
