# Toscana: Monumenti & altro – dati

Repository **pubblico** con tutto ciò che l'app scarica: pacchetti delle città, audioguide, catalogo e novità dell'app. Il codice dell'app è in `toscana-app`.

## Contenuto

- `pacchetti/<id>/`: dati (`dati/*.json`), foto (`assets/`), `manifest.json` e `manifest_prova.json`, `audioguide/testi.json`.
- `audioguide/<id>/<lingua>/`: MP3 e `indice.json` (generati dal workflow).
- `catalogo.json`: elenco delle città (fonte; l'app ne tiene una copia, aggiornata con `npm run sync:catalogo`).
- `app_novita.json`: popup "Nuova versione disponibile" dell'app.
- `strumenti/`: script Python. `docs/privacy/`: informativa. `.github/workflows/`: audioguide, mappa, controlli, notifica mail.

## Nuova città

1. `python3 strumenti/nuova_citta.py firenze "Firenze" 43.7696 11.2558 Firenze` crea `pacchetti/firenze/` con i file vuoti validi e la voce in `catalogo.json` (stato `in_preparazione`).
2. Compila `luoghi.json` e gli altri dati; mappa con il workflow **Mappa**; servizi con `servizi_osm.py`; rete pedonale con `costruisci_rete.py`; mezzi con un convertitore (esempio: `esempio_converti_autobus_gtfs.py`); foto con `scarica_commons.py`.
3. `python3 strumenti/prepara_pacchetto.py pacchetti/firenze` genera `dati/immagini.json`, i manifest e il pacchetto prova (10 luoghi di `anteprima`).
4. In `catalogo.json`: `stato` `disponibile`, `motto` nelle 5 lingue, `anteprima`, `pacchetto` e `pacchetto_prova` (gli indirizzi li stampa lo script della nuova città).

L'`id` può avere trattini (es. `san-gimignano`): il motore lo legge da `citta.json`.

## Segreti da impostare nel repository

- `GOOGLE_TTS_API_KEY` (workflow audioguide).
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` (mail di esito delle attività pianificate).

## Note

- Il repo è pubblico: niente chiavi né password nei file.
- I contenuti a pagamento oggi non sono protetti (chiunque conosca gli indirizzi può scaricarli); si potranno spostare su un hosting con controllo dell'acquisto cambiando solo gli indirizzi.
