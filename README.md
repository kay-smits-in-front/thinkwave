# thinkwave

Guiding innovation through smaller measurable steps.

Flask-backend voor Thinkwave: accounts, teams en (later) metingen. Het PlayCanvas-bord blijft los gehost en praat straks via een API met deze app.

## Rollen

| Rol | Kan |
|---|---|
| Beheerder (`admin`) | Hoort bij een organisatie, voegt gewone accounts toe tot de limiet van het abonnement (10, 50 of onbeperkt) |
| Gewoon account (`member`) | Alleen inloggen, ziet alleen het eigen team |

De database dwingt twee regels zelf af: een gewoon account hoort altijd bij een team, en dat team hoort bij dezelfde organisatie.

## Lokaal draaien

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app wsgi db upgrade
flask --app wsgi run
```

## Tests

```bash
pytest                                                   # SQLite in het geheugen
TEST_DATABASE_URL=postgresql://user@localhost/db pytest  # tegen PostgreSQL
```

## Deployment (Render)

`render.yaml` maakt een webservice en een eigen PostgreSQL-database aan. In het Render-dashboard vul je `TRUSTED_HOSTS` in. `SECRET_KEY` wordt gegenereerd en `DATABASE_URL` komt uit de database. In productie weigert de app te starten bij ontbrekende of onveilige instellingen. Het schema wordt bij elke deploy bijgewerkt met `flask db upgrade`.
