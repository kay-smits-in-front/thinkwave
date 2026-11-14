# Beveiliging

## Een kwetsbaarheid melden

Meld kwetsbaarheden privé via het tabblad **Security** van deze repository ("Report a vulnerability").
Zet ze niet in een openbare issue en deel geen echte gegevens.

## Uitgangspunten

- Geen gegevens van anderen in pagina's: e-mailadressen worden afgeschermd, wachtwoord-hashes en interne ID's komen nergens naar buiten, er is geen JSON-API met klantdata.
- Toegang wordt op de server bepaald (`app/scoping.py`) en door de database afgedwongen; een gewoon account ziet alleen zijn eigen team, een beheerder alleen zijn eigen organisatie.
- Alle invoer heeft een lengtegrens en een toegestane vorm; keuzes komen uit vaste lijsten.
- Geen JavaScript en geen externe bronnen (strikte Content-Security-Policy).
- Geheimen staan nooit in de code, alleen in omgevingsvariabelen.
