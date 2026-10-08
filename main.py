"""Radar Créations — commandes.

    python main.py daily            ce que fait le robot chaque matin : envoi des alertes + site
    python main.py send [--dry-run] envoie les alertes des parutions pas encore envoyées
    python main.py site             reconstruit le site (7 derniers jours) dans dist/
    python main.py subscribers      affiche les abonnés actifs et leurs départements
    python main.py test             tests

Variables d'environnement (secrets, jamais dans le code) :
    STRIPE_SECRET_KEY   clé secrète Stripe (lecture des abonnés)
    BREVO_API_KEY       clé API Brevo (envoi des e-mails)
Sans elles, tout fonctionne en mode test : abonnés lus dans subscribers.local.json,
e-mails écrits dans out/emails/.
"""
import argparse
import datetime as dt
import json
import os
import sys

from radar import data, mailer, site, subscribers

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, "state.json")


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"dernier_envoi": None, "historique": []}


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def cmd_send(config, dry_run=False, today=None):
    """Envoie, en un seul e-mail par abonné, toutes les parutions depuis le dernier envoi.
    On s'arrête à la veille : la parution du jour peut encore être en cours de mise en ligne."""
    today = today or dt.date.today()
    until = today - dt.timedelta(days=1)
    state = load_state()
    last = dt.date.fromisoformat(state["dernier_envoi"]) if state["dernier_envoi"] else until - dt.timedelta(days=1)
    days = [last + dt.timedelta(days=i) for i in range(1, (until - last).days + 1)][-7:]
    by_day = data.fetch_days(days)
    published = [d for d in days if by_day[d]]
    if not published:
        print("Aucune nouvelle parution depuis le", last)
        if days and not dry_run:
            state["dernier_envoi"] = days[-1].isoformat()
            save_state(state)
        return 0
    rows = [r for d in published for r in by_day[d]]
    subs = subscribers.load(config, ROOT)
    out_dir = os.path.join(ROOT, "out", "emails")
    if dry_run:
        os.environ.pop("BREVO_API_KEY", None)
    sent = skipped = 0
    for sub in subs:
        if not sub["departements"]:
            print(f"  ! {sub['email']} : aucun département reconnu dans « {sub['demande']} »")
            skipped += 1
            continue
        msg = mailer.build(sub, rows, [d.isoformat() for d in published], config)
        if not msg:
            skipped += 1
            continue
        subject, body_html, body_text, csv_bytes = msg
        name = f"nouvelles-societes-{published[-1].isoformat()}.csv"
        mailer.send(sub["email"], subject, body_html, body_text, csv_bytes, name, config, out_dir)
        sent += 1
    print(f"Parutions {', '.join(d.isoformat() for d in published)} : {len(rows)} sociétés, "
          f"{len(subs)} abonnés, {sent} e-mails{' (mode test : out/emails/)' if dry_run or not os.environ.get('BREVO_API_KEY') else ''}, "
          f"{skipped} sans envoi")
    if not dry_run:
        state["dernier_envoi"] = published[-1].isoformat()
        state["historique"] = (state["historique"] + [{"date": published[-1].isoformat(), "societes": len(rows),
                                                        "abonnes": len(subs), "emails": sent}])[-400:]
        save_state(state)
    return 0


def cmd_site(config):
    # Pas de mise en ligne publique avec des mentions légales incomplètes (LCEN).
    if os.environ.get("GITHUB_ACTIONS") and "COMPLÉTER" in config["legal"].get("address", "").upper():
        print("Mise en ligne bloquée : renseigner legal.address dans config.json.")
        return 1
    days = data.last_days(8)
    by_day = data.fetch_days(days, cache_dir=os.path.join(ROOT, "out", "cache"))
    n = site.build(config, by_day, os.path.join(ROOT, "dist"))
    print(f"Site : {n} pages dans dist/ ({sum(len(v) for v in by_day.values())} sociétés sur 8 jours)")
    return 0


def cmd_subscribers(config):
    subs = subscribers.load(config, ROOT)
    for s in subs:
        print(f"{s['statut']:<9} {s['email']:<35} {len(s['departements'])}/{s['max']} dép. "
              f"{', '.join(s['departements'][:10])} (saisi : « {s['demande']} »)")
    print(f"{len(subs)} abonné(s)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["daily", "send", "site", "subscribers", "test"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    config = load_config()
    if args.command == "send":
        return cmd_send(config, args.dry_run)
    if args.command == "site":
        return cmd_site(config)
    if args.command == "subscribers":
        return cmd_subscribers(config)
    if args.command == "test":
        import unittest
        suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"))
        return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1
    # daily : les alertes d'abord (ce que paient les abonnés), le site ensuite
    code = cmd_send(config)
    code |= cmd_site(config)
    return code


if __name__ == "__main__":
    sys.exit(main())
