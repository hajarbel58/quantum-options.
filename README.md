# QUANTUM OPTIONS

Application Flask de valorisation d'options, simulation brownienne et intégration Monte Carlo.

## Mise en ligne gratuite : GitHub puis Render

1. Décompresser ce dossier sur votre ordinateur.
2. Sur https://github.com/new, créer un dépôt nommé `quantum-options` (privé possible).
3. Dans ce dépôt, choisir **uploading an existing file** ou **Add file > Upload files**.
4. Déposer le CONTENU du dossier : `app.py`, `requirements.txt`, `render.yaml`, `templates`, `static`, etc. Ces fichiers doivent être à la racine du dépôt. Ne pas téléverser uniquement le ZIP.
5. Enregistrer avec **Commit changes**.
6. Sur https://dashboard.render.com, se connecter puis choisir **New > Blueprint**, connecter GitHub et sélectionner ce dépôt.
7. Vérifier que le service `quantum-options` utilise le plan **Free**, puis lancer le déploiement. Le fichier `render.yaml` contient la configuration. Aucun service payant ni base de données n'est nécessaire.
8. Quand le service indique **Live**, ouvrir l'adresse `https://…onrender.com` affichée par Render. C'est le lien à placer dans le portfolio.

### Si vous utilisez New > Web Service au lieu de Blueprint

- Runtime : Python 3.
- Plan : **Free**.
- Build Command : `pip install -r requirements.txt`
- Start Command : `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 app:app`
- Environment : `PYTHON_VERSION=3.11.11`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`.
- Root Directory : laisser vide si `app.py` est à la racine du dépôt.
- Health Check Path : `/health`.

Documentation : https://render.com/docs/deploy-flask et https://render.com/docs/free
Le plan gratuit met le site en veille après 15 minutes sans visite ; le premier accès suivant peut prendre du temps. Les ressources et quotas gratuits restent ceux définis par Render. Vérifier le plan Free avant de valider.

## Démonstration sans dépendre de Yahoo Finance

Ouvrir **Pricing** et saisir :

- Prix du sous-jacent : `100` (le ticker peut rester vide).
- Strike : `100`.
- Maturity : `365` jours.
- Rate : `0.05`.
- Volatility : `0.2`.
- European, Call, Black-Scholes.

Le prix attendu est d'environ **10.45 USD**.
Pour une option américaine, choisir **Monte Carlo**. Le champ des dates d'exercice intervient uniquement pour ce cas.

Si aucun prix manuel n'est saisi, le ticker est utilisé pour demander le dernier cours disponible à Yahoo Finance. Cet accès peut être limité ou indisponible sur un serveur d'hébergement. Le prix manuel permet de continuer à utiliser les modèles.

## Exécution locale

Dans un terminal ouvert dans ce dossier :

```sh
python -m venv .venv
```

Sur Windows PowerShell :

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://127.0.0.1:5000.
Gunicorn est utilisé sur le serveur Linux Render ; en local Windows, utiliser `python app.py`.

## Changements par rapport au ZIP d'origine

- Ajout de la configuration Render, de Gunicorn et des dépendances.
- Retrait de Graphviz et du chemin Windows.
- Retrait du modèle binomial de l'application publiée et de la page d'accueil, conformément au choix de l'autrice.
- Retrait du calcul des Greeks Monte Carlo. Le code d'origine ne calculait pas les Greeks Black-Scholes : cette version n'en ajoute pas.
- Ajout d'une saisie manuelle du spot et de la devise ; correction de l'affichage de la devise.
- Correction de l'actualisation et de la décision d'exercice de Longstaff-Schwartz : comparaison au payoff immédiat et conservation des flux réalisés, plutôt que remplacement des flux par leur prédiction de régression.
- Correction du facteur de volatilité appliqué deux fois dans la simulation du mouvement brownien géométrique.
- Analyse des expressions d'intégration par une liste d'opérations mathématiques autorisées ; pas d'évaluation Python libre des expressions saisies.
- Limites de taille des simulations adaptées à une démonstration sur serveur gratuit ; mode debug désactivé.
- Les anciens scripts, PDF et classeurs non utilisés par les routes Flask n'ont pas été inclus dans cette version de déploiement. Le ZIP d'origine reste votre source pour ces documents.

## Vérifications

Vérifications locales : accès aux trois pages et à une image, calcul Black-Scholes de référence, comparaison Monte Carlo / Black-Scholes, contrôle de bornes d'un put américain, intégration d'une constante et d'un polynôme, rejet d'expressions non autorisées, simulations browniennes et réponses POST des outils.

La mise en ligne sur votre compte Render et l'accès réel à Yahoo Finance depuis Render doivent encore être vérifiés après le déploiement. Aucun site n'est créé par la simple préparation de ce dossier.
