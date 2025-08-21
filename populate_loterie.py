import csv
import re
import os
from pathlib import Path

# On écrit dans historiques_*.csv (écrasement systématique, pas de fusion)
LOTERIES = {
    "1": {
        "nom": "6/49",
        "txt_in": "tirages_649.txt",
        "hist_csv": "data/historiques_649.csv",
        "doublons_csv": "data/doublons_649.csv",
        "draw_size": 6
    },
    "2": {
        "nom": "Lotto Max",
        "txt_in": "tirages_lotto_max.txt",
        "hist_csv": "data/historiques_lotto_max.csv",
        "doublons_csv": "data/doublons_lotto_max.csv",
        "draw_size": 7
    },
    "3": {
        "nom": "Grande Vie",
        "txt_in": "tirages_grande_vie.txt",
        "hist_csv": "data/historiques_grande_vie.csv",
        "doublons_csv": "data/doublons_grande_vie.csv",
        "draw_size": 5
    }
}

def _parse_line_to_nums(line: str, draw_size: int):
    """
    Nettoie une ligne: retire un éventuel bonus '(xx)', extrait les nombres (1-2 chiffres).
    Retourne une liste de chaînes SANS zéro devant si exactement draw_size nombres trouvés, sinon None.
    """
    line = line.strip()
    # Retire un bonus éventuel en fin de ligne : " ... (nn)"
    line = re.sub(r'\s*\(\d{1,2}\)\s*', '', line)
    # Extrait tous les nombres 1-2 chiffres
    nums = re.findall(r'\b\d{1,2}\b', line)
    if len(nums) != draw_size:
        return None
    # On normalise SANS zéro devant (ex: "02" -> "2")
    return [str(int(n)) for n in nums]

def populate_loterie(config, ordre='C'):
    seen_in_input = {}
    combos_final = []
    doublons_list = []

    # 1) Parse uniquement le fichier source (AUCUNE LECTURE d'historique existant)
    with open(config["txt_in"], encoding='utf-8') as f:
        for raw in f:
            # Date éventuelle au début (facultatif, utile pour log des doublons)
            date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', raw.strip())
            date = date_match.group(1) if date_match else 'DATE_INCONNUE'

            nums = _parse_line_to_nums(raw, config["draw_size"])
            if not nums:
                continue

            # Clé de dédup interne = combinaison triée (pour éviter "1 2 3" vs "3 2 1")
            key_sorted = tuple(sorted(nums, key=lambda x: int(x)))
            if key_sorted in seen_in_input:
                doublons_list.append([date] + list(key_sorted))
            else:
                seen_in_input[key_sorted] = date
                # On stocke trié par combinaison pour une sortie propre/constante
                combos_final.append(list(key_sorted))

    # 2) Tri global si demandé
    if ordre == 'C':
        # Trie lexicographique mais basé sur les valeurs numériques
        combos_final.sort(key=lambda comb: [int(x) for x in comb])

    # 3) Écriture (écrasement) dans historiques_*.csv — format texte "n1 n2 n3 ..."
    os.makedirs(os.path.dirname(config["hist_csv"]), exist_ok=True)
    with open(config["hist_csv"], 'w', encoding='utf-8') as f:
        for combo in combos_final:
            f.write(" ".join(str(int(n)) for n in combo) + "\n")

    # 4) Doublons internes (si trouvés) — écrit en CSV classique pour inspection
    if doublons_list:
        with open(config["doublons_csv"], 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Date'] + [f'Num{i+1}' for i in range(config["draw_size"])])
            writer.writerows(doublons_list)

    # 5) Logs de synthèse
    print(f"\n🎯 Loterie : {config['nom']}")
    print(f"🧩 Mode : {'Croissant (ordre lignes trié)' if ordre == 'C' else 'Mélangé (ordre brut)'}")
    print(f"➕ {len(doublons_list)} doublon(s) détecté(s) (dans le fichier d’entrée)")
    print(f"✅ {len(combos_final)} combinaisons sauvegardées (écrasement) → {config['hist_csv']}")
    if doublons_list:
        print(f"📝 Doublons internes enregistrés → {config['doublons_csv']}")

    # 6) Affichage complet dans le terminal (format simple avec espaces, sans index)
    print("\n=== Historique complet ===")
    for combo in combos_final:
        print(" ".join(str(int(n)) for n in combo))

if __name__ == "__main__":
    print("🎰 Choisissez une loterie à traiter :")
    print("1. 6/49")
    print("2. Lotto Max")
    print("3. Grande Vie")
    choix = input("> ").strip()

    if choix in LOTERIES:
        print("🔢 Ordre croissant (C) ou brut (M) ?")
        ordre = input("> ").strip().upper()
        if ordre not in ('C', 'M'):
            print("❗ Choix invalide, C par défaut.")
            ordre = 'C'
        populate_loterie(LOTERIES[choix], ordre)
    else:
        print("❌ Choix invalide. Entrez 1, 2 ou 3.")



