# Civilina — Dashboard Streamlit

Réplique fidèle du fichier civilina.pbix (mêmes mesures, mêmes chiffres, 3 pages).

## Lancer en local
```
pip install -r requirements.txt
streamlit run app.py
```
Puis ouvrir http://localhost:8501

## Déployer gratuitement (lien public, sans compte requis pour le visiteur)
1. Mettre ce dossier dans un repo GitHub (public ou privé)
2. Aller sur https://share.streamlit.io → "New app" → connecter le repo → sélectionner app.py
3. Récupérer le lien (ex: https://civilina-xxxx.streamlit.app) et le partager

## Fichiers
- app.py — application principale
- activites.csv / suivi_hebdo.csv — données nettoyées (identiques au .pbix)
- banner.png — bannière Civilina (extraite du .pbix)
