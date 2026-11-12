# thinkwave

Guiding innovation through smaller measurable steps.

Thinkwave, de AI-innovatietool, herbouwd in Flask + HTMX. Het oude PlayCanvas-bord (`playcanv.as/p/f8c12796`) blijft ongewijzigd bestaan.

## Wat de app doet

- **Accounts**: zelf registreren (je wordt beheerder van je organisatie), inloggen met e-mail en wachtwoord. Geen projectcode meer.
- **Projecten** op drie borden met dezelfde data: jeugd (kleurrijk), werk en management (rustig).
- **Bord**: 36 stappen in vier fasen (Research, Ideation, Development, Business). Elke stap kost weken op een tijdlijn van 24 maanden en levert impact op. Hoeveel hangt af van de *sweetspot*: hoe dicht de fase bij het ideale punt van de stap zit (zelfde regels als het oude bord, zie `app/board.py`).
- **Evaluatiemomenten** op 1/4, 2/4 en 3/4 van de tijdlijn en een eindscherm, met de teksten uit het oude bord.
- **Voorgestelde stappen**: hoogste verwachte impact nu; bij gelijkspel wint wat gebruikers in andere projecten het best beoordeelden.
- **Logboek**: per stap vastleggen wat het opleverde en een eigen oordeel 1–5. Plus een eindoordeel per project. Dit is de leerdata.
- **Ideeën, verslagen, checklist en metingen** (ideeën, budget, opgeloste problemen, onderzoeksuren, gesproken mensen, stagiairs).

De inhoud van het bord staat in `app/content/board.json` (overgenomen uit de gepubliceerde spreadsheet van het oude bord). `flask --app wsgi seed` zet de stappen in de database.

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
flask --app wsgi seed
flask --app wsgi run      # open http://127.0.0.1:5000
```

## Tests

```bash
pytest                                                   # SQLite in het geheugen
TEST_DATABASE_URL=postgresql://user@localhost/db pytest  # tegen PostgreSQL
```

## Deployment (Render)

`render.yaml` maakt een webservice en een eigen PostgreSQL-database aan. In het Render-dashboard vul je `TRUSTED_HOSTS` in. `SECRET_KEY` wordt gegenereerd en `DATABASE_URL` komt uit de database. In productie weigert de app te starten bij ontbrekende of onveilige instellingen. Het schema en de stappen worden bij elke deploy bijgewerkt met `flask db upgrade` en `flask seed`.
