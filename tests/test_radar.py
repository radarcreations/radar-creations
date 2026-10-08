import csv
import datetime as dt
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import main
from radar import data, mailer, site, subscribers

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "bodacc_sample.json"), encoding="utf-8") as f:
    RAW = json.load(f)
ROWS = [r for r in (data.parse(x) for x in RAW) if r]
CONFIG = main.load_config()


class Parse(unittest.TestCase):
    def test_only_companies(self):
        self.assertEqual(len(ROWS), 16)  # 19 annonces dont 3 entrepreneurs individuels exclus
        self.assertTrue(all(r["siren"].isdigit() and len(r["siren"]) == 9 for r in ROWS))

    def test_no_activity_companies_are_labelled(self):
        sans = [r for r in ROWS if r["activite"].startswith("Sans activité")]
        self.assertTrue(sans)
        self.assertTrue(all(r["secteur"] == "holding" for r in sans))

    def test_short_forms(self):
        self.assertEqual(data.forme_courte("Société par actions simplifiée (à associé unique)"), "SASU")
        self.assertEqual(data.forme_courte("Société civile immobilière"), "SCI")
        self.assertEqual(data.forme_courte("Société à responsabilité limitée"), "SARL")

    def test_classify(self):
        self.assertEqual(data.classify("Travaux de plomberie et chauffage", "SAS"), "btp")
        self.assertEqual(data.classify("Restauration rapide sur place ou à emporter", "SAS"), "restauration")
        self.assertEqual(data.classify("Prise de participations dans toutes sociétés", "SAS"), "holding")
        self.assertEqual(data.classify("n'importe quoi", "Société civile immobilière"), "immobilier")
        self.assertEqual(data.classify("Élevage de chèvres", "SAS"), "autres")


class Departements(unittest.TestCase):
    def test_codes_and_names(self):
        p = subscribers.parse_departements
        self.assertEqual(p("33, 24 et 47", 3), ["33", "24", "47"])
        self.assertEqual(p("33 24 47 40", 3), ["33", "24", "47"])  # limité à la formule
        self.assertEqual(p("Haute-Loire", 1), ["43"])
        self.assertEqual(p("Loire", 1), ["42"])
        self.assertEqual(p("2a, 2B", 2), ["2A", "2B"])
        self.assertEqual(p("5", 1), ["05"])
        self.assertEqual(p("974", 1), ["974"])
        self.assertEqual(len(p("", 101)), len(data.DEPARTEMENTS))
        self.assertEqual(p("rien", 1), [])


class Mail(unittest.TestCase):
    def test_build_filters_departments(self):
        sub = {"email": "a@b.fr", "departements": ["33"], "max": 1}
        subject, body, text, csv_bytes = mailer.build(sub, ROWS, ["2026-09-30"], CONFIG)
        g = [r for r in ROWS if r["departement"] == "33"]
        self.assertIn(f"{len(g)} nouvelle", subject)
        for r in g:
            self.assertIn(r["siren"], body)
        reader = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(reader), len(g) + 1)
        self.assertIn('charset="utf-8"', body)

    def test_nothing_to_send(self):
        sub = {"email": "a@b.fr", "departements": ["976"], "max": 1}
        self.assertIsNone(mailer.build(sub, [r for r in ROWS if r["departement"] != "976"], ["2026-09-30"], CONFIG))

    def test_no_director_names(self):
        # les noms des dirigeants (champ « administration ») ne doivent jamais être diffusés
        names = [json.loads(x["listepersonnes"])["personne"].get("administration", "") for x in RAW
                 if '"pm"' in x["listepersonnes"]]
        sub = {"email": "a@b.fr", "departements": list(data.DEPARTEMENTS), "max": 101}
        _, body, _, csv_bytes = mailer.build(sub, ROWS, ["2026-09-30"], CONFIG)
        for adm in names:
            for part in adm.split(";"):
                person = part.split(":")[-1].strip().split(",")[0].strip()
                if len(person) > 4 and person.isupper():
                    self.assertNotIn(person, body)


class Send(unittest.TestCase):
    def test_sends_yesterday_then_nothing(self):
        today = dt.date(2026, 10, 1)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(main, "STATE", os.path.join(tmp, "state.json")), \
                mock.patch.object(main, "ROOT", tmp), \
                mock.patch.object(data, "fetch_days", lambda days, cache_dir=None: {d: ROWS for d in days}), \
                mock.patch.object(subscribers, "load", lambda c, r: [
                    {"email": "a@b.fr", "departements": ["33"], "max": 1, "demande": "33", "statut": "t"}]), \
                mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BREVO_API_KEY", None)
            main.cmd_send(CONFIG, today=today)
            state = main.load_state()
            self.assertEqual(state["dernier_envoi"], "2026-09-30")
            self.assertTrue(os.path.exists(os.path.join(tmp, "out", "emails", "a_at_b.fr.html")))
            main.cmd_send(CONFIG, today=today)  # même jour : rien de nouveau
            self.assertEqual(len(main.load_state()["historique"]), 1)


class Site(unittest.TestCase):
    def test_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            n = site.build(CONFIG, {dt.date(2026, 9, 30): ROWS}, tmp)
            self.assertEqual(n, 1 + 1 + len(data.DEPARTEMENTS) + len(site.VILLES) + len(site.SECTEUR_PAGES) + 3)
            for path in ("villes/bordeaux-33", "secteurs/immobilier"):
                self.assertTrue(os.path.exists(os.path.join(tmp, path, "index.html")))
            with open(os.path.join(tmp, "creations", "33-gironde", "index.html"), encoding="utf-8") as f:
                page = f.read()
            self.assertIn("Gironde (33)", page)
            self.assertIn("30 septembre 2026", page)
            self.assertTrue(os.path.exists(os.path.join(tmp, "sitemap.xml")))
            self.assertEqual(site.date_fr("2026-10-01"), "1er octobre 2026")

    def test_city_groups_arrondissements(self):
        self.assertEqual(site.ville_key("MARSEILLE 8E ARRONDISSEMENT"), "marseille")
        self.assertEqual(site.ville_key("Marseille 1er Arrondissement"), "marseille")
        self.assertEqual(site.ville_key("SAINT-ÉTIENNE"), site.slug("Saint-Étienne"))


if __name__ == "__main__":
    unittest.main()
