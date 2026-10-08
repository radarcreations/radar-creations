"""Site statique : accueil, une page par département (mise à jour chaque jour), pages légales, sitemap."""
import datetime as dt
import html
import json
import os
import shutil
import unicodedata

from .data import DEPARTEMENTS, SECTEUR_LABELS
from .mailer import short

E = html.escape
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]


def slug(text):
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return "".join(c if c.isalnum() else "-" for c in t).strip("-").replace("--", "-")


def dep_path(code):
    return f"creations/{code.lower()}-{slug(DEPARTEMENTS[code])}/"


def date_fr(iso):
    d = dt.date.fromisoformat(iso)
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"


CSS = """
:root{--ink:#16212c;--muted:#5b6876;--line:#dfe5ec;--bg:#ffffff;--soft:#f3f6f9;--accent:#1f5f8b;--accent2:#174a6d;--ok:#1d7a4f}
@media (prefers-color-scheme:dark){:root{--ink:#e8eef4;--muted:#a3b0bd;--line:#2c3743;--bg:#10161d;--soft:#18212b;--accent:#6fb0de;--accent2:#8cc3ea;--ok:#5cc293}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
a{color:var(--accent)}.wrap{max-width:980px;margin:auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line)}header.top .wrap{display:flex;justify-content:space-between;align-items:center;height:60px;gap:12px}
.logo{font-weight:800;text-decoration:none;color:var(--ink);letter-spacing:-.02em}.logo span{color:var(--accent)}
nav a{margin-left:16px;text-decoration:none;color:var(--muted);font-size:15px}
.hero{padding:56px 0 36px}.hero h1{font-size:clamp(28px,5vw,44px);line-height:1.15;margin:0 0 14px;letter-spacing:-.02em}
.hero p.lead{font-size:19px;color:var(--muted);max-width:680px;margin:0 0 24px}
.btn{display:inline-block;background:var(--accent);color:#fff;padding:13px 22px;border-radius:8px;text-decoration:none;font-weight:700}
.btn:hover{background:var(--accent2)}.btn.ghost{background:transparent;color:var(--accent);border:1.5px solid var(--accent)}
.note{font-size:14px;color:var(--muted);margin-top:10px}
section{padding:34px 0;border-top:1px solid var(--line)}h2{font-size:26px;margin:0 0 16px;letter-spacing:-.01em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
.card{border:1px solid var(--line);border-radius:10px;padding:18px;background:var(--bg)}.card h3{margin:0 0 6px;font-size:17px}
.card p{margin:0;color:var(--muted);font-size:15px}
.price{font-size:34px;font-weight:800}.price small{font-size:15px;font-weight:500;color:var(--muted)}
.plan.best{border:2px solid var(--accent)}.plan ul{padding-left:18px;color:var(--muted);font-size:15px}
.stat{font-size:30px;font-weight:800;color:var(--accent)}
table.list{width:100%;border-collapse:collapse;font-size:14px}table.list th{text-align:left;color:var(--muted);font-weight:600;border-bottom:2px solid var(--line);padding:8px 6px}
table.list td{border-bottom:1px solid var(--line);padding:8px 6px;vertical-align:top}.tag{display:inline-block;font-size:12px;background:var(--soft);border-radius:20px;padding:1px 9px;color:var(--muted)}
.scroll{overflow-x:auto}.deps{columns:3 220px;font-size:15px}.deps a{text-decoration:none}.deps span{color:var(--muted);font-size:13px}
.cta{background:var(--soft);border-radius:12px;padding:22px;margin:24px 0}
details{border-bottom:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:600}
footer{border-top:1px solid var(--line);padding:26px 0;color:var(--muted);font-size:14px}footer a{color:var(--muted);margin-right:14px}
.legal h2{font-size:20px;margin-top:26px}
@media (max-width:600px){nav a.hide-sm{display:none}.hero{padding:36px 0 24px}}
"""


def page(config, path, title, description, body, depth):
    root = "../" * depth
    brand = config["brand"]
    canonical = (config.get("site_url") or "").rstrip("/") + "/" + path
    gsv = config.get("google_site_verification")
    verif = f'<meta name="google-site-verification" content="{E(gsv)}">' if gsv else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(description)}">
<link rel="canonical" href="{E(canonical)}">{verif}<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(description)}"><meta name="color-scheme" content="light dark">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%231f5f8b'/%3E%3Ccircle cx='16' cy='16' r='5' fill='white'/%3E%3C/svg%3E">
<style>{CSS}</style></head><body>
<header class="top"><div class="wrap"><a class="logo" href="{root}index.html">Radar<span>Créations</span></a>
<nav><a href="{root}creations/index.html">Créations par département</a><a class="hide-sm" href="{root}index.html#tarifs">Tarifs</a></nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap"><a href="{root}mentions-legales.html">Mentions légales</a><a href="{root}cgv.html">Conditions de vente</a>
<a href="{root}confidentialite.html">Données et confidentialité</a><br>
Données publiques issues du BODACC (DILA), réutilisées sous Licence Ouverte 2.0. {E(brand)} n'est pas un service de l'État.</div></footer>
</body></html>"""


def plans_html(config, root=""):
    out = ['<div class="grid">']
    for i, p in enumerate(config["plans"]):
        link = p.get("payment_link")
        best = " best" if i == 1 else ""
        # Tant que Stripe n'est pas branché, pas de faux bouton de paiement.
        button = (f'<a class="btn" href="{E(link)}">Essayer {config["trial_days"]} jours gratuits</a>' if link
                  else '<span class="btn" aria-disabled="true" style="opacity:.6;cursor:default">Ouverture prochaine</span>')
        out.append(f"""<div class="card plan{best}"><h3>{E(p['name'])}</h3>
<div class="price">{p['price']} €<small> / mois</small></div>
<ul>{''.join(f'<li>{E(x)}</li>' for x in p['features'])}</ul>
{button}</div>""")
    out.append("</div>")
    out.append(f'<p class="note">Sans engagement : résiliable en un clic depuis chaque e-mail. '
               f'{E(config["legal"].get("vat_note", ""))}</p>')
    return "".join(out)


def company_rows(rows, limit=None):
    out = ['<div class="scroll"><table class="list"><thead><tr><th>Société</th><th>Ville</th><th>Activité</th>'
           '<th>Publiée le</th></tr></thead><tbody>']
    for r in rows[:limit] if limit else rows:
        out.append(f'<tr><td><b>{E(r["nom"])}</b><br><span class="tag">{E(r["forme_courte"])}</span> '
                   f'<span class="tag">{E(SECTEUR_LABELS[r["secteur"]].split(" (")[0])}</span></td>'
                   f'<td>{E(r["ville"])}</td><td>{E(short(r["activite"], 110))}</td>'
                   f'<td>{E(date_fr(r["date_parution"]))}</td></tr>')
    out.append("</tbody></table></div>")
    return "".join(out)


def build(config, rows_by_day, out_dir, assets_dir=None):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    days = sorted(d for d, rows in rows_by_day.items() if rows)
    all_rows = [r for d in days for r in rows_by_day[d]]
    last = days[-1].isoformat() if days else dt.date.today().isoformat()
    period = f"du {date_fr(days[0].isoformat())} au {date_fr(last)}" if days else ""
    by_dep = {}
    for r in all_rows:
        by_dep.setdefault(r["departement"], []).append(r)
    urls = []

    def write(path, content):
        full = os.path.join(out_dir, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        urls.append(path.replace("index.html", ""))

    # -------- accueil
    sample_dep = max(by_dep, key=lambda k: len(by_dep[k])) if by_dep else "33"
    n_week = len(all_rows)
    who = [
        ("Experts-comptables", "Une société qui vient de naître cherche son comptable : soyez le premier à la contacter."),
        ("Assureurs et courtiers", "Responsabilité civile, multirisque, prévoyance du dirigeant : tout est à souscrire."),
        ("Banques et financement", "Compte professionnel, terminal de paiement, crédit d'équipement."),
        ("Agences web et communication", "Site internet, logo, fiche Google : les nouvelles sociétés partent de zéro."),
        ("Gestion locative et notaires", "Des centaines de SCI créées chaque semaine : des projets immobiliers à accompagner."),
        ("Fournisseurs et grossistes", "Restaurants, commerces, entreprises du bâtiment : de nouveaux clients à équiper."),
    ]
    body = f"""<div class="hero"><h1>Les sociétés créées près de chez vous, chaque matin dans votre boîte mail</h1>
<p class="lead">Chaque jour, des centaines de sociétés sont immatriculées en France. Recevez celles de votre département,
triées par secteur, avec leur adresse et un fichier Excel prêt pour votre prospection.</p>
<a class="btn" href="#tarifs">Essayer {config['trial_days']} jours gratuits</a>
<a class="btn ghost" href="{dep_path(sample_dep)}index.html">Voir un exemple</a>
<p class="note">{f"{n_week:,}".replace(",", " ")} sociétés créées et publiées {E(period)}.</p></div>
<section><h2>Pour qui ?</h2><div class="grid">{''.join(f'<div class="card"><h3>{E(a)}</h3><p>{E(b)}</p></div>' for a, b in who)}</div></section>
<section><h2>Comment ça marche</h2><div class="grid">
<div class="card"><h3>1. Choisissez vos départements</h3><p>À l'inscription, indiquez le ou les départements qui vous intéressent.</p></div>
<div class="card"><h3>2. Recevez l'alerte du jour</h3><p>Chaque jour de parution du BODACC, un e-mail liste les nouvelles sociétés, regroupées par secteur.</p></div>
<div class="card"><h3>3. Prospectez</h3><p>Dénomination, forme, capital, activité, adresse du siège, SIREN, liens vers la fiche officielle, et un fichier CSV pour Excel.</p></div>
</div></section>
<section id="tarifs"><h2>Tarifs</h2>{plans_html(config)}</section>
<section><h2>Questions fréquentes</h2>
<details><summary>D'où viennent les données ?</summary><p>Du BODACC, le Bulletin officiel des annonces civiles et commerciales, où chaque immatriculation de société est publiée. Ces données publiques sont réutilisables sous Licence Ouverte. Nous les récupérons chaque jour, les trions par département et par secteur, et vous les envoyons.</p></details>
<details><summary>Pourquoi pas les auto-entrepreneurs ?</summary><p>Les entrepreneurs individuels sont des personnes physiques : nous ne diffusons pas leurs données. L'alerte contient uniquement des sociétés (SAS, SARL, SCI, etc.).</p></details>
<details><summary>Y a-t-il des numéros de téléphone ou des e-mails ?</summary><p>Non : le BODACC ne les publie pas. Vous recevez l'adresse du siège, l'activité et le SIREN, avec un lien vers la fiche officielle de l'entreprise.</p></details>
<details><summary>Combien de sociétés par jour ?</summary><p>Cela dépend du département : de quelques-unes par semaine dans les départements ruraux à plusieurs dizaines par jour à Paris. Consultez la page de votre département pour voir les chiffres de la semaine.</p></details>
<details><summary>Comment résilier ?</summary><p>Chaque e-mail contient un lien « Gérer ou résilier mon abonnement ». La résiliation prend effet à la fin de la période payée, sans démarche supplémentaire.</p></details>
<details><summary>Puis-je changer de département ?</summary><p>Résiliez puis souscrivez à nouveau en indiquant les nouveaux départements : c'est immédiat.</p></details>
</section>"""
    write("index.html", page(config, "", f"{config['brand']} : les nouvelles sociétés de votre département chaque matin",
                             "Recevez chaque jour par e-mail les sociétés créées dans votre département : adresse, activité, "
                             "capital, SIREN et fichier Excel. Pour experts-comptables, assureurs, banques, agences.", body, 0))

    # -------- hub des départements
    items = "".join(f'<div><a href="{dep_path(c).replace("creations/", "")}index.html">{E(n)} ({c})</a> '
                    f'<span>{len(by_dep.get(c, []))}</span></div>' for c, n in DEPARTEMENTS.items())
    body = f"""<div class="hero"><h1>Créations de sociétés par département</h1>
<p class="lead">Les sociétés immatriculées et publiées au BODACC {E(period)}, département par département. Mis à jour chaque jour.</p></div>
<div class="deps">{items}</div>
<div class="cta"><b>Recevez celles de votre département chaque matin.</b> <a href="../index.html#tarifs">Voir les tarifs</a></div>"""
    write("creations/index.html", page(config, "creations/", "Créations de sociétés par département, cette semaine",
                                       "Liste des sociétés créées cette semaine dans chaque département, d'après le BODACC. "
                                       "Mise à jour quotidienne.", body, 1))

    # -------- une page par département
    for code, name in DEPARTEMENTS.items():
        rows = sorted(by_dep.get(code, []), key=lambda r: (r["date_parution"], r["nom"]), reverse=True)
        counts = {}
        for r in rows:
            counts[r["secteur"]] = counts.get(r["secteur"], 0) + 1
        stats = "".join(f'<div class="card"><div class="stat">{n}</div><p>{E(SECTEUR_LABELS[k])}</p></div>'
                        for k, n in sorted(counts.items(), key=lambda kv: -kv[1])[:6])
        listing = company_rows(rows) if rows else "<p>Aucune société publiée cette semaine dans ce département.</p>"
        body = f"""<div class="hero"><h1>Nouvelles sociétés : {E(name)} ({code})</h1>
<p class="lead">{len(rows)} société{'s' if len(rows) != 1 else ''} créée{'s' if len(rows) != 1 else ''} et publiée{'s' if len(rows) != 1 else ''} au BODACC {E(period)}.</p>
<a class="btn" href="../../index.html#tarifs">Les recevoir chaque matin</a>
<p class="note">L'alerte par e-mail ajoute l'adresse complète du siège, le capital, le SIREN et un fichier Excel.</p></div>
{f'<div class="grid">{stats}</div>' if stats else ''}
<section><h2>Liste de la semaine</h2>{listing}</section>
<div class="cta"><b>Ne ratez plus aucune création en {E(name)}.</b> Un e-mail chaque jour de parution, résiliable en un clic.
<br><br><a class="btn" href="../../index.html#tarifs">Essayer {config['trial_days']} jours gratuits</a></div>"""
        write(dep_path(code) + "index.html", page(
            config, dep_path(code), f"Nouvelles sociétés créées en {name} ({code}) cette semaine",
            f"{len(rows)} sociétés créées en {name} ({code}) {period} : SAS, SARL, SCI… Liste mise à jour chaque jour "
            f"d'après le BODACC.", body, 2))

    # -------- pages légales
    L = config["legal"]
    legal_pages = {
        "mentions-legales.html": ("Mentions légales", f"""<h1>Mentions légales</h1>
<h2>Éditeur</h2><p>{E(L['publisher'])}<br>{E(L['status'])}<br>SIRET : {E(L['siret'])}<br>Adresse : {E(L['address'])}<br>
Contact : {E(config['contact_email'])}<br>Directeur de la publication : {E(L['director'])}<br>{E(L.get('vat_note', ''))}</p>
<h2>Hébergement</h2><p>{E(L['host'])}</p>
<h2>Source des données</h2><p>Bulletin officiel des annonces civiles et commerciales (BODACC), Direction de l'information légale
et administrative (DILA). Données réutilisées sous Licence Ouverte / Open Licence version 2.0. Les informations sont
reproduites telles que publiées ; seuls le classement par secteur et la mise en forme sont ajoutés.</p>"""),
        "cgv.html": ("Conditions de vente", f"""<h1>Conditions générales de vente</h1>
<h2>Service</h2><p>{E(config['brand'])} envoie par e-mail, chaque jour de parution du BODACC, la liste des sociétés nouvellement
immatriculées dans les départements choisis par l'abonné, accompagnée d'un fichier CSV. Le service s'adresse aux professionnels.</p>
<h2>Prix et paiement</h2><p>Les prix sont indiqués sur la page d'accueil, par mois. {E(L.get('vat_note', ''))} Le paiement est
réalisé par carte via Stripe. Un essai gratuit de {config['trial_days']} jours est proposé à la première souscription ;
sans résiliation avant la fin de l'essai, l'abonnement mensuel démarre automatiquement.</p>
<h2>Durée et résiliation</h2><p>L'abonnement est mensuel, sans engagement, renouvelé automatiquement. Il est résiliable à tout
moment via le lien présent dans chaque e-mail ; la résiliation prend effet à la fin de la période en cours. Les périodes
entamées ne sont pas remboursées.</p>
<h2>Données</h2><p>Les données proviennent du BODACC et sont fournies telles que publiées. L'éditeur ne garantit pas leur
exhaustivité et ne peut être tenu responsable d'une erreur de publication ou d'un retard de la source. L'abonné s'engage à
utiliser les données dans le respect de la réglementation, notamment du RGPD et des règles de prospection commerciale.</p>
<h2>Litiges</h2><p>Droit français. En cas de difficulté, contact : {E(config['contact_email'])}.</p>"""),
        "confidentialite.html": ("Données et confidentialité", f"""<h1>Données et confidentialité</h1>
<h2>Données des abonnés</h2><p>Nous conservons uniquement l'adresse e-mail et les départements choisis, pour envoyer l'alerte.
Le paiement est traité par Stripe ; l'envoi des e-mails par Brevo. Aucune donnée n'est revendue. Ce site n'utilise ni
cookie ni outil de mesure d'audience.</p>
<h2>Données diffusées</h2><p>Seules des sociétés (personnes morales) sont diffusées, à partir des annonces publiques du BODACC.
Les entrepreneurs individuels sont exclus. Les noms des dirigeants ne sont pas repris.</p>
<h2>Vos droits</h2><p>Pour toute demande (accès, rectification, opposition, retrait d'une société de nos listes) :
{E(config['contact_email'])}. Vous pouvez aussi saisir la CNIL (cnil.fr).</p>"""),
    }
    for fname, (title, content) in legal_pages.items():
        write(fname, page(config, fname, f"{title} · {config['brand']}", title, f'<div class="legal" style="padding:30px 0">{content}</div>', 0))

    # -------- sitemap et robots
    base = (config.get("site_url") or "").rstrip("/")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{E(base + '/' + u)}</loc><lastmod>{last}</lastmod></url>" for u in urls]
    sm.append("</urlset>")
    with open(os.path.join(out_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    with open(os.path.join(out_dir, ".nojekyll"), "w") as f:
        f.write("")
    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump({"maj": last, "societes_7_jours": n_week}, f)
    return len(urls)
