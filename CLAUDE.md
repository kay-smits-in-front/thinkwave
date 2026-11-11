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
  - Navy `#082235` (tekst, donkere vlakken), rood `#FF0000` (logo en accenten), knoprood `#D10000` (contrast met wit).
  - Koppen: Montserrat 700/800. Tekst: Inter.
  - Beeld in `app/static/brand/`: `logo-red.png`, `logo-white.png`, `waves-white.png`, `astronaut.webp`.
- De vier fasen van het bord: Research, Ideation, Development, Business.
- Elk invoerveld een zichtbaar label, knoppen beginnen met een werkwoord, zichtbare focus, 44px tikvlakken,
  `prefers-reduced-motion` respecteren.
