"""Liste des abonnés actifs. Aucune base de données : Stripe est la seule source de vérité.

Chaque abonné a souscrit via un lien de paiement Stripe qui contient un champ « departements »
(texte libre, par ex. « 33, 24 » ou « France »). Le nombre de départements autorisé vient des
métadonnées du prix Stripe (`max_departements`) ou, à défaut, de config.json.
Pour tester sans Stripe : subscribers.local.json (voir subscribers.local.example.json).
"""
import base64
import json
import os
import re
import urllib.parse
import urllib.request

from .data import DEPARTEMENTS

STRIPE = "https://api.stripe.com/v1"


def parse_departements(text, max_n):
    """« 33, 24 et 47 » → ['33', '24', '47'] (limité à max_n). « France » → tous."""
    if max_n >= len(DEPARTEMENTS):  # formule France entière
        return list(DEPARTEMENTS)
    t = (text or "").strip().lower()
    found = []
    for tok in re.findall(r"\b(2a|2b|97[1-6]|\d{1,2})\b", t):
        code = tok.upper() if tok.startswith("2") and tok[1:].isalpha() else tok.zfill(2)
        if code in DEPARTEMENTS and code not in found:
            found.append(code)
    # noms écrits en toutes lettres (« Gironde »)
    # les plus longs d'abord, pour que « Haute-Loire » ne soit pas lu comme « Loire »
    for code, name in sorted(DEPARTEMENTS.items(), key=lambda kv: -len(kv[1])):
        pattern = r"(?<![\w-])" + re.escape(name.lower()) + r"(?![\w-])"
        if re.search(pattern, t):
            t = re.sub(pattern, " ", t)
            if code not in found:
                found.append(code)
    return found[:max_n]


def _stripe_get(path, params, key):
    url = f"{STRIPE}/{path}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, headers={
        "Authorization": "Basic " + base64.b64encode(f"{key}:".encode()).decode()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _plan_max(sub, config):
    for item in sub.get("items", {}).get("data", []):
        price = item.get("price") or {}
        meta = price.get("metadata") or {}
        if meta.get("max_departements"):
            return int(meta["max_departements"])
        for plan in config["plans"]:
            if price.get("unit_amount") in (plan["price"] * 100, plan.get("price_year", 0) * 100):
                return plan["max_departements"]
    return 1


def from_stripe(key, config):
    subs = []
    params = {"status": "all", "limit": 100, "expand[]": "data.customer"}
    while True:
        page = _stripe_get("subscriptions", params, key)
        for s in page["data"]:
            if s["status"] not in ("active", "trialing"):
                continue
            customer = s.get("customer") or {}
            email = customer.get("email")
            sessions = _stripe_get("checkout/sessions", {"subscription": s["id"], "limit": 1}, key)["data"]
            text = ""
            if sessions:
                fields = sessions[0].get("custom_fields") or []
                # Stripe génère la clé à partir du libellé : on accepte « departements », « dpartements »…
                # et, à défaut, le seul champ du formulaire.
                chosen = [f for f in fields if "part" in (f.get("key") or "").lower()] or fields[:1]
                for f in chosen:
                    text = (f.get("text") or {}).get("value") or (f.get("dropdown") or {}).get("value") or ""
                email = email or (sessions[0].get("customer_details") or {}).get("email")
            max_n = _plan_max(s, config)
            if email:
                subs.append({"email": email, "departements": parse_departements(text, max_n),
                             "demande": text, "max": max_n, "statut": s["status"]})
        if not page.get("has_more"):
            break
        params["starting_after"] = page["data"][-1]["id"]
    return subs


def load(config, root):
    key = os.environ.get("STRIPE_SECRET_KEY")
    if key:
        return from_stripe(key, config)
    path = os.path.join(root, "subscribers.local.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return [{"email": s["email"], "departements": parse_departements(s["departements"], s.get("max", 1)),
                 "demande": s["departements"], "max": s.get("max", 1), "statut": "local"} for s in raw]
    return []
