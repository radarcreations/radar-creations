# Radar Créations

**Abonnement B2B : chaque matin, les sociétés créées la veille dans les départements choisis, par e-mail, avec un fichier Excel.**
Pour les professionnels dont les nouvelles sociétés sont les futurs clients : experts-comptables, assureurs, banques, agences web, gestion locative, fournisseurs.

Tout est automatique : Stripe encaisse et gère les résiliations, un robot GitHub envoie les alertes et met le site à jour chaque matin. **Aucun contact client, aucun serveur, aucune base de données.**

## Pourquoi cette idée (et pas une autre)

| Constat | Source |
|---|---|
| Ce marché existe et des pros paient déjà : Leaddar vend exactement cette alerte quotidienne **79 €/mois** | [leaddar.fr](https://leaddar.fr/) |
| Autres acteurs payants sur les mêmes données : BODACC.io dès 9 €/mois, Guichet Sociétés 69 €/mois, fichiers de créations à 0,18 € le contact | [recherche](https://www.easyfichiers.com/fr/fichier-creation-entreprises), [bodacc.io](https://bodacc.io/en) |
| Matière première abondante : 301 300 sociétés créées en 2025 (+6 %), soit ~600 à 700 publiées par jour ouvré | [INSEE Première n° 2092](https://www.insee.fr/fr/statistiques/8721354) |
| Données gratuites et réutilisables commercialement (Licence Ouverte 2.0), avec une API ouverte | [API BODACC (DILA)](https://bodacc-datadila.opendatasoft.com) |
| Les entreprises sont des clients qui paient un abonnement plus facilement, et plus cher, que les particuliers | — |

Idées écartées après recherche : alertes d'appels d'offres (des alertes gratuites existent déjà : BOAMP, France Marchés), radar des permis de construire (les permis des particuliers sont anonymisés, données publiées avec un ou deux mois de retard), produits grand public (il faut 50 à 70 abonnés pour le même revenu).

**Le calcul** : à 19 €/mois, il reste ~18,50 € après Stripe. 50 €/semaine ≈ 217 €/mois ≈ **12 abonnés** (environ 15 après les cotisations de micro-entrepreneur). 100 €/semaine ≈ **24 à 30 abonnés**. Quelques abonnés « 3 départements » (39 €) ou « France » (79 €) réduisent ce nombre.

**Ce qui n'est pas garanti** : que ces abonnés arrivent. Les données sont aussi consultables gratuitement (bodacc.fr, annuaire-entreprises), et des concurrents existent ; ce qui est vendu, c'est le tri et la livraison chaque matin. Les visiteurs viendront surtout de Google via les 101 pages départementales mises à jour chaque jour : comptez **2 à 6 mois** avant un trafic régulier, sans certitude.

## Ce qui est prêt

- `radar/data.py` : récupération des créations au BODACC, sociétés uniquement, classement en 10 secteurs.
- `radar/subscribers.py` : lecture des abonnés actifs directement dans Stripe, départements saisis à l'inscription (« 33 », « Gironde, 24 »…).
- `radar/mailer.py` : e-mail par abonné (regroupé par secteur) + CSV pour Excel, envoi par Brevo.
- `radar/site.py` : site vitrine, page Tarifs, 101 pages « Nouvelles sociétés en <département> » mises à jour chaque jour, mentions légales, CGV, confidentialité, sitemap.
- `.github/workflows/quotidien.yml` : le robot de chaque matin.
- `tests/` : 10 tests sur de vraies annonces.

Données personnelles : les entrepreneurs individuels (personnes physiques) sont exclus et les noms des dirigeants ne sont jamais repris (un test le vérifie).

## Commandes

```bash
python main.py test                 # tests
python main.py send --dry-run       # alertes en mode test → out/emails/
python main.py site                 # site → dist/
python main.py subscribers          # abonnés actifs et départements
```

Python 3.10+ uniquement, aucune dépendance.

## Mise en route — ce que toi seul peux faire (environ 3 à 4 h, une fois)

1. **Statut** : micro-entreprise (gratuit, sur formalites.entreprises.gouv.fr ou autoentrepreneur.urssaf.fr), activité de services.
2. **Adresse dans les mentions légales** : `config.json` → `legal.address`, plus le SIRET dès réception. Une domiciliation évite de publier ton adresse personnelle.
3. **Nom de domaine** (environ 10 €/an, conseillé) : un e-mail d'envoi à ton nom de domaine arrive bien mieux en boîte de réception qu'une adresse Gmail.
4. **Brevo** (gratuit jusqu'à 300 e-mails/jour) : créer le compte, valider l'adresse ou le domaine d'envoi, créer une clé API.
5. **Stripe** :
   - créer 3 produits avec un prix mensuel : 19 €, 39 €, 79 € ; sur chaque prix, ajouter la métadonnée `max_departements` = `1`, `3` ou `101` ;
   - pour chacun, créer un **lien de paiement** avec essai gratuit de 7 jours et un **champ personnalisé** de type texte, clé `departements`, libellé « Département(s) à suivre (ex. 33 ou 33, 24, 47) » ;
   - activer le **portail client** (Paramètres → Facturation → Portail client) et copier son lien de connexion ;
   - créer une **clé restreinte** en lecture seule sur « Subscriptions » et « Checkout Sessions ».
6. **Remplir `config.json`** : `site_url`, `sender_email`, les 3 `payment_link`, `stripe_portal_url`.
7. **GitHub** : créer un dépôt **public** (GitHub Pages est gratuit pour les dépôts publics ; aucun secret n'est dans le code), y pousser ce dossier, puis :
   - Settings → Pages → Source : **GitHub Actions** ;
   - Settings → Secrets and variables → Actions : ajouter `STRIPE_SECRET_KEY` et `BREVO_API_KEY` ;
   - Actions → « Envoi quotidien » → **Run workflow** pour le premier lancement.
8. **Google Search Console** : ajouter le site et déclarer `sitemap.xml`.
9. **Test réel** : t'abonner toi-même au plan à 19 € (tu peux résilier pendant l'essai) et vérifier l'e-mail du lendemain.

## Ensuite : 15 à 30 minutes par semaine

- Regarder le tableau de bord Stripe (abonnés, essais, résiliations).
- Vérifier que le robot a tourné (onglet Actions de GitHub : coche verte). En cas d'échec, GitHub t'envoie un e-mail ; relancer avec « Run workflow ».
- Une fois par mois : `state.json` contient l'historique des envois (sociétés, abonnés, e-mails).

Les messages éventuels arrivent sur l'adresse de contact des mentions légales (obligatoire). La FAQ du site répond aux questions courantes, et la résiliation se fait seule via le portail Stripe.

## Décision à 3 mois (chiffres Stripe et Search Console)

- Des visites mais pas d'essais → revoir la page d'accueil et les prix.
- Des essais mais peu de conversions → l'alerte ne convainc pas : interroger les données (secteurs les plus regardés), ajouter un filtre par secteur.
- Peu de visites → les pages départementales ne se positionnent pas : ajouter des pages par grande ville et par secteur.

## Améliorations possibles

| Priorité | Idée |
|---|---|
| 1 | Filtre par secteur dans l'abonnement (deuxième champ Stripe) |
| 2 | Pages par grande ville et par secteur (« nouvelles SCI à Bordeaux ») pour plus de trafic Google |
| 3 | Récapitulatif hebdomadaire pour ceux qui préfèrent un e-mail par semaine |
| 3 | Ajout des radiations et des cessions (autres familles du BODACC) |
