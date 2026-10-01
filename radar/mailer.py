"""E-mail d'alerte : les nouvelles sociétés des départements de l'abonné, avec un CSV joint.

Envoi par l'API Brevo (gratuite jusqu'à 300 e-mails par jour). Sans clé BREVO_API_KEY,
les e-mails sont écrits dans out/emails/ (mode test).
"""
import base64
import csv
import html
import io
import json
import os
import urllib.request

from .data import DEPARTEMENTS, SECTEUR_LABELS

CSV_COLUMNS = [
    ("date_parution", "Date de parution"), ("nom", "Dénomination"), ("forme_courte", "Forme"),
    ("capital", "Capital (€)"), ("secteur_label", "Secteur"), ("activite", "Activité déclarée"),
    ("adresse", "Adresse du siège"), ("cp", "Code postal"), ("ville", "Ville"), ("departement", "Département"),
    ("debut_activite", "Début d'activité"), ("siren", "SIREN"), ("fiche", "Fiche entreprise"),
    ("url_bodacc", "Annonce BODACC"),
]


def fiche_url(siren):
    return f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}" if siren else ""


def to_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([label for _, label in CSV_COLUMNS])
    for r in rows:
        r = dict(r, secteur_label=SECTEUR_LABELS.get(r["secteur"], ""), fiche=fiche_url(r["siren"]))
        cap = r.get("capital")
        r["capital"] = "" if cap is None else (f"{cap:.0f}" if cap == int(cap) else f"{cap:.2f}".replace(".", ","))
        w.writerow([r.get(k, "") for k, _ in CSV_COLUMNS])
    # BOM : Excel ouvre directement le fichier avec les accents
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _fmt_date(iso):
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def short(text, n=150):
    text = text or ""
    if len(text) <= n:
        return text[:1].upper() + text[1:]
    cut = text[:n].rsplit(" ", 1)[0]
    return cut[:1].upper() + cut[1:] + "…"


def build(sub, rows, dates, config):
    """Renvoie (sujet, html, texte, csv) ou None s'il n'y a rien à envoyer."""
    mine = [r for r in rows if r["departement"] in sub["departements"]]
    if not mine:
        return None
    brand = config["brand"]
    days = " et ".join(_fmt_date(d) for d in dates) if len(dates) <= 2 else f"du {_fmt_date(dates[0])} au {_fmt_date(dates[-1])}"
    if len(sub["departements"]) >= len(DEPARTEMENTS):
        zone = "France entière"
    else:
        zone = ", ".join(f"{DEPARTEMENTS[c]} ({c})" for c in sub["departements"])
    n = len(mine)
    subject = f"{n} nouvelle{'s' if n > 1 else ''} société{'s' if n > 1 else ''} · {zone if len(zone) < 40 else 'vos départements'}"

    groups = {}
    for r in mine:
        groups.setdefault(r["secteur"], []).append(r)
    order = sorted(groups, key=lambda k: (k == "autres", -len(groups[k])))

    accent = "#1f5f8b"
    parts = [f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;padding:16px">
<div style="font-family:Arial,Helvetica,sans-serif;max-width:720px;margin:auto;color:#1d2733">
<p style="font-size:13px;color:#667;margin:0 0 4px">{html.escape(brand)} · {html.escape(zone)}</p>
<h1 style="font-size:22px;margin:0 0 6px">{n} société{'s' if n > 1 else ''} créée{'s' if n > 1 else ''}</h1>
<p style="font-size:14px;color:#445;margin:0 0 18px">Publiées au BODACC {html.escape(days)}. Le fichier joint (CSV, s'ouvre dans Excel) contient toutes les colonnes.</p>
<table style="border-collapse:collapse;font-size:13px;margin-bottom:18px">"""]
    for k in order:
        parts.append(f'<tr><td style="padding:2px 14px 2px 0">{html.escape(SECTEUR_LABELS[k])}</td>'
                     f'<td style="padding:2px 0;font-weight:bold;text-align:right">{len(groups[k])}</td></tr>')
    parts.append("</table>")
    text = [f"{brand} · {zone}", f"{n} société(s) créée(s), publiées au BODACC {days}.", ""]
    for k in order:
        parts.append(f'<h2 style="font-size:16px;color:{accent};border-bottom:2px solid {accent};'
                     f'padding-bottom:4px;margin:22px 0 8px">{html.escape(SECTEUR_LABELS[k])} ({len(groups[k])})</h2>')
        text.append(f"== {SECTEUR_LABELS[k]} ({len(groups[k])}) ==")
        for r in groups[k]:
            cap = f" · capital {r['capital']:,.0f} €".replace(",", " ") if r.get("capital") else ""
            addr = ", ".join(x for x in [r["adresse"], f"{r['cp']} {r['ville']}".strip()] if x)
            parts.append(
                f'<div style="padding:8px 0;border-bottom:1px solid #e3e8ee">'
                f'<div style="font-size:14px"><b>{html.escape(r["nom"])}</b> '
                f'<span style="color:#778">{html.escape(r["forme_courte"])}{html.escape(cap)}</span></div>'
                f'<div style="font-size:13px;color:#445">{html.escape(addr)}</div>'
                f'<div style="font-size:12px;color:#667;margin-top:2px">{html.escape(short(r["activite"]))}</div>'
                f'<div style="font-size:12px;margin-top:3px"><a href="{fiche_url(r["siren"])}" style="color:{accent}">'
                f'Fiche entreprise</a> · <a href="{r["url_bodacc"]}" style="color:{accent}">Annonce BODACC</a></div></div>')
            text.append(f"- {r['nom']} ({r['forme_courte']}) · {addr}\n  {short(r['activite'])}\n  {fiche_url(r['siren'])}")
        text.append("")
    portal = config.get("stripe_portal_url") or ""
    parts.append(f"""<p style="font-size:12px;color:#889;margin-top:26px;line-height:1.5">
Données publiques issues du BODACC (DILA, Licence Ouverte 2.0), réorganisées par {html.escape(brand)}.
Sociétés uniquement : les entrepreneurs individuels ne sont pas inclus.<br>
Rappel : la prospection par e-mail d'une entreprise doit porter sur son activité professionnelle et proposer
un moyen simple de refuser les messages suivants.<br>
{'<a href="' + html.escape(portal) + '" style="color:#889">Gérer ou résilier mon abonnement</a>' if portal else ''}
</p></div></body></html>""")
    if portal:
        text.append(f"Gérer ou résilier mon abonnement : {portal}")
    return subject, "".join(parts), "\n".join(text), to_csv(mine)


def send(to, subject, html_body, text_body, csv_bytes, csv_name, config, out_dir):
    key = os.environ.get("BREVO_API_KEY")
    if not key:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.join(out_dir, to.replace("@", "_at_"))
        with open(base + ".html", "w", encoding="utf-8") as f:
            f.write(html_body.replace("<head>", f"<head><title>{html.escape(subject)}</title>", 1))
        with open(base + ".csv", "wb") as f:
            f.write(csv_bytes)
        return "test"
    payload = {
        "sender": {"name": config["brand"], "email": config["sender_email"]},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body,
        "attachment": [{"name": csv_name, "content": base64.b64encode(csv_bytes).decode()}],
    }
    if config.get("reply_to"):
        payload["replyTo"] = {"email": config["reply_to"]}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email", data=json.dumps(payload).encode(),
                                 headers={"api-key": key, "Content-Type": "application/json",
                                          "Accept": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status
