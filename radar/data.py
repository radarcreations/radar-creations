"""Récupère les créations de sociétés publiées au BODACC (open data, Licence Ouverte Etalab 2.0).

Source : https://bodacc-datadila.opendatasoft.com — jeu « annonces-commerciales », famille « creation ».
On ne garde que les personnes morales (sociétés). Les entrepreneurs individuels sont exclus :
ce sont des personnes physiques, et leurs données ne sont pas proposées.
"""
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request

API = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/exports/json"

DEPARTEMENTS = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes", "09": "Ariège", "10": "Aube", "11": "Aude",
    "12": "Aveyron", "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal", "16": "Charente",
    "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme",
    "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère", "30": "Gard", "31": "Haute-Garonne", "32": "Gers",
    "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire",
    "38": "Isère", "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
    "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère",
    "49": "Maine-et-Loire", "50": "Manche", "51": "Marne", "52": "Haute-Marne", "53": "Mayenne",
    "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord",
    "60": "Oise", "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône",
    "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie",
    "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres",
    "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse", "85": "Vendée",
    "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort",
    "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis", "94": "Val-de-Marne",
    "95": "Val-d'Oise", "971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion",
    "976": "Mayotte",
}

# Secteurs : premier qui correspond (l'ordre compte). Mots cherchés dans l'objet social.
SECTEURS = [
    ("holding", "Holdings & gestion de participations",
     r"holding|prise[s]? de participation|valeurs mobili|portefeuille de titres|participations? dans toutes"),
    ("immobilier", "Immobilier (SCI, location, transaction)",
     r"immobili|location de (biens|logements|locaux)|marchand de biens|lotissement|promotion|construction.vente"),
    ("btp", "BTP & travaux",
     r"b[aâ]timent|travaux|ma[cç]onnerie|plomberie|[ée]lectricit|r[ée]novation|couverture|charpente|menuiserie"
     r"|peinture|carrelage|terrassement|chauffage|climatisation|isolation|second [oœ]uvre|gros [oœ]uvre|btp"
     r"|paysag|piscine|serrurerie|fa[cç]ade|plaquiste|cloisons"),
    ("restauration", "Restauration & alimentation",
     r"restaura|boulang|p[aâ]tisser|traiteur|alimentaire|snack|d[ée]bit de boissons|\bbar\b|caf[ée]|pizz"
     r"|food|cuisine|[ée]picerie|boucherie|vente [àa] emporter|sur place ou [àa] emporter"),
    ("sante", "Santé, beauté & bien-être",
     r"sant[ée]|m[ée]dical|infirmi|kin[ée]|param[ée]dical|pharmac|dentaire|bien-[êe]tre|esth[ée]ti|coiffure"
     r"|beaut[ée]|massage|sport|fitness|yoga|ost[ée]opa|psycholog"),
    ("numerique", "Informatique & numérique",
     r"informatique|logiciel|num[ée]rique|d[ée]veloppement (web|d'applications|de sites)|digital|saas|internet"
     r"|cyber|intelligence artificielle|data|application[s]? mobile"),
    ("transport", "Transport & logistique",
     r"transport|livraison|logistique|taxi|vtc|d[ée]m[ée]nagement|coursier|fret|ambulance"),
    ("conseil", "Conseil, formation & services aux entreprises",
     r"conseil|consult|formation|accompagnement|audit|marketing|communication|recrutement|coaching|gestion administrative"
     r"|secr[ée]tariat|nettoyage|s[ée]curit[ée] priv|[ée]v[ée]nementiel|agence"),
    ("commerce", "Commerce & e-commerce",
     r"commerce|vente|achat|n[ée]goce|import|export|distribution|boutique|magasin|revente"),
]


def classify(activite, forme):
    a = (activite or "").lower()
    f = (forme or "").lower()
    if a.startswith("sans activité"):
        return "holding"
    if "civile immobili" in f or "construction vente" in f or "attribution" in f:
        return "immobilier"
    for key, _label, pattern in SECTEURS:
        if re.search(pattern, a):
            return key
    return "autres"


SECTEUR_LABELS = {k: label for k, label, _ in SECTEURS}
SECTEUR_LABELS["autres"] = "Autres activités"

FORMES_COURTES = [
    ("par actions simplifiée (à associé unique)", "SASU"), ("par actions simplifiée", "SAS"),
    ("responsabilité limitée (à associé unique)", "EURL"), ("responsabilité limitée", "SARL"),
    ("civile immobilière", "SCI"), ("civile de construction vente", "SCCV"), ("civile de moyens", "SCM"),
    ("anonyme", "SA"), ("en nom collectif", "SNC"), ("d'exercice libéral", "SEL"),
    ("intérêt économique", "GIE"), ("coopérative", "SCOP / coopérative"), ("civile", "Société civile"),
]


def forme_courte(forme):
    f = (forme or "").lower()
    for needle, short in FORMES_COURTES:
        if needle in f:
            return short
    return forme or ""


def _addr(a):
    if not a:
        return "", "", ""
    rue = " ".join(x for x in [a.get("numeroVoie"), a.get("indiceRepetition"), a.get("typeVoie"), a.get("nomVoie")] if x)
    if a.get("complGeographique"):
        rue = f"{rue}, {a['complGeographique']}" if rue else a["complGeographique"]
    return rue.strip(), a.get("codePostal", ""), a.get("ville", "")


def _capital(cap):
    if not cap:
        return None
    if cap.get("montantCapital"):
        try:
            return float(cap["montantCapital"])
        except ValueError:
            return None
    m = re.search(r"([\d.]+)", cap.get("capitalVariable", ""))
    return float(m.group(1)) if m else None


def _first(x):
    return x[0] if isinstance(x, list) else x


def parse(record):
    """Annonce BODACC → fiche société, ou None si ce n'est pas une société."""
    try:
        personnes = json.loads(record.get("listepersonnes") or "{}")
        etabs = json.loads(record.get("listeetablissements") or "{}")
        acte = json.loads(record.get("acte") or "{}")
    except json.JSONDecodeError:
        return None
    p = _first(personnes.get("personne"))
    if not p or p.get("typePersonne") != "pm":
        return None
    e = _first(etabs.get("etablissement")) or {}
    rue, cp, ville = _addr(p.get("adresseSiegeSocial") or e.get("adresse"))
    siren = (p.get("numeroImmatriculation") or {}).get("numeroIdentification", "").replace(" ", "")
    forme = p.get("formeJuridique", "")
    activite = re.sub(r"\s+", " ", e.get("activite", "") or "").strip()
    sans_activite = "sans activit" in ((acte.get("creation") or {}).get("categorieCreation") or "").lower()
    if not activite and sans_activite:
        activite = "Sans activité déclarée à l'immatriculation"
    dep = str(record.get("numerodepartement") or "").zfill(2)
    return {
        "id": record.get("id"),
        "siren": siren,
        "nom": (p.get("denomination") or "").strip(),
        "sigle": p.get("sigle") or "",
        "forme": forme,
        "forme_courte": forme_courte(forme),
        "capital": _capital(p.get("capital")),
        "activite": activite,
        "secteur": classify(activite, forme),
        "adresse": rue,
        "cp": cp or record.get("cp", ""),
        "ville": ville or record.get("ville", ""),
        "departement": dep,
        "debut_activite": acte.get("dateCommencementActivite") or acte.get("dateImmatriculation") or "",
        "date_parution": record.get("dateparution"),
        "url_bodacc": record.get("url_complete"),
    }


def fetch_day(day, retries=3):
    """Toutes les sociétés créées publiées au BODACC à la date `day` (datetime.date)."""
    where = f'familleavis="creation" and dateparution=date\'{day.isoformat()}\''
    url = API + "?" + urllib.parse.urlencode({"where": where})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                records = json.load(r)
            break
        except Exception:  # noqa: BLE001 - réseau : on réessaie
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    out = [s for s in (parse(r) for r in records) if s]
    out.sort(key=lambda s: (s["departement"], s["ville"], s["nom"]))
    return out


def fetch_days(days, cache_dir=None):
    """Plusieurs jours, avec cache disque facultatif (un fichier par jour publié)."""
    import os
    result = {}
    for d in days:
        path = os.path.join(cache_dir, f"{d.isoformat()}.json") if cache_dir else None
        if path and os.path.exists(path) and d < dt.date.today():
            with open(path, encoding="utf-8") as f:
                result[d] = json.load(f)
            continue
        rows = fetch_day(d)
        result[d] = rows
        if path:
            os.makedirs(cache_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False)
    return result


def last_days(n, until=None):
    """Les n derniers jours ouvrés (le BODACC paraît du mardi au samedi, parfois lundi) — on prend tous les jours."""
    until = until or dt.date.today()
    return [until - dt.timedelta(days=i) for i in range(n)][::-1]
