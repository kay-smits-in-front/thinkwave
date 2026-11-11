# Thinkwave

Thinkwave is de AI-innovatietool. Slogan: "Develop AI projects. Develop with AI."
Flask-app in Python. Pagina's zijn Jinja-templates, later met HTMX. Geen eigen JavaScript-frameworks.

## Werkwijze
- Alleen Python. Eén functie of class per stap. Doe wat gevraagd is, niet meer.
- Elke functie doet één ding. Modern Python (type hints, `|`-unions, dataclasses/StrEnum).
- Tests met pytest in `tests/`.

## Webpagina's
- Gebruik bij elke webpagina de skill `design-taste-frontend` (installeren: `npx skills add Leonxlnx/taste-skill -g -a claude-code`).
  Pas de ontwerpregels toe binnen Flask/Jinja; de skill staat niet in de repo.
- Huisstijl staat in `app/static/css/thinkwave.css` (tokens op `:root`). Gebruik die tokens, geen losse kleuren.
  - Stijl van het platform: blauwe achtergrond met golven (`brand/waves-bg.svg`), rood logoblok, rode knop.
  - Navy `#082235` (tekst), oceaan `#1d3e58` (achtergrond), rood `#FF0000` (knop, knoptekst minimaal 20px vet voor contrast).
  - Fasekleuren: Research `#00c2f0`, Ideation `#ffc400`, Development `#18e07a`, Business `#ff4d4d`.
  - Koppen: Montserrat 700/800, hoofdletters. Tekst: Inter.
  - Beeld in `app/static/brand/`: `logo-red.png`, `logo-white.png`, `waves-bg.svg`.
- De vier fasen van het bord: Research, Ideation, Development, Business.
- Elk invoerveld een zichtbaar label, knoppen beginnen met een werkwoord, zichtbare focus, 44px tikvlakken,
  `prefers-reduced-motion` respecteren.
