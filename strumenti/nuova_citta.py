#!/usr/bin/env python3
"""Crea lo scheletro di una nuova città del motore unico.

Uso: python3 strumenti/nuova_citta.py <id> "<Nome>" <latitudine> <longitudine> [provincia]
Esempio: python3 strumenti/nuova_citta.py firenze "Firenze" 43.7696 11.2558 Firenze

L'id è il nome della cartella del pacchetto: minuscolo, senza accenti (trattini ammessi, es. san-gimignano).

Crea pacchetti/<id>/ con i file di dati vuoti ma validi (il motore li legge tutti), le cartelle delle foto,
audioguide/testi.json e aggiunge la città a catalogo.json con stato "in_preparazione" e pacchetto null.
Restano da fare: luoghi.json, mappa (workflow "Mappa"), servizi, mezzi, itinerari, foto; poi
python3 strumenti/prepara_pacchetto.py pacchetti/<id> e, in catalogo.json, "stato": "disponibile" e gli URL dei manifest.
"""
import json
import os
import re
import sys

RADICE = 'https://raw.githubusercontent.com/federicocoppola73/toscana-dati/main/pacchetti/'


def scrivi(percorso, dati):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, 'w', encoding='utf-8') as f:
        json.dump(dati, f, ensure_ascii=False, indent=1)
        f.write('\n')


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    id_citta, nome = sys.argv[1], sys.argv[2]
    lat, lon = float(sys.argv[3]), float(sys.argv[4])
    provincia = sys.argv[5] if len(sys.argv) > 5 else nome
    if not re.fullmatch(r'[a-z]+(-[a-z]+)*', id_citta):
        sys.exit('id non valido: solo lettere minuscole senza accenti e trattini')
    cartella = os.path.join('pacchetti', id_citta)
    if os.path.exists(cartella):
        sys.exit(f'{cartella} esiste già')
    d = os.path.join(cartella, 'dati')
    punto = {'latitudine': lat, 'longitudine': lon}
    nota = lambda t: f'{nome}: {t}'
    scrivi(f'{d}/citta.json', {'_nota': 'Dati generali della città: nome nei testi e funzioni', 'id': id_citta, 'nome': nome,
                               'marea': False, 'centro': {**punto, 'zoom': 3}, 'riferimento': punto, 'partenze': {}})
    scrivi(f'{d}/app.json', {'expo': {'name': nome, 'version': '1.0.0'}})
    scrivi(f'{d}/aguzza.json', {'_nota': nota('schede "aguzza la vista" da scrivere'), 'itinerari': [], 'domande': []})
    scrivi(f'{d}/autobus.json', {'_nota': nota('linee e fermate dei mezzi da generare'), 'validita': [], 'linee': [], 'fermate': {}, 'fermataLinee': {}})
    scrivi(f'{d}/orari_autobus.json', {'_nota': nota('orari dei mezzi da generare'), 'validita': [], 'servizi': [], 'date': {}, 'capolinea': [], 'orari': {}})
    scrivi(f'{d}/vaporetti.json', {'_nota': nota('nessun vaporetto'), 'validita': [], 'linee': [], 'fermate': {}, 'alias': {}})
    scrivi(f'{d}/orari_vaporetti.json', {'_nota': nota('nessun orario vaporetti'), 'validita': [], 'servizi': [], 'date': {}, 'capolinea': [], 'orari': {}})
    scrivi(f'{d}/rete.json', {'_nota': nota('rete pedonale da generare'), 'nodi': [], 'archi': [], 'luoghi': {}})
    scrivi(f'{d}/cibi.json', {'_nota': nota('cibi e prodotti tipici'), 'cibi': []})
    scrivi(f'{d}/curiosita.json', {'_nota': nota('luoghi curiosi'), 'curiosita': []})
    scrivi(f'{d}/eventi.json', {'_nota': nota('eventi (aggiornati ogni 15 giorni)'), 'eventi': []})
    scrivi(f'{d}/itinerari.json', {'_nota': nota('nessun itinerario per ora'), 'itinerari': []})
    scrivi(f'{d}/luoghi.json', {'versione': 1, 'luoghi': []})
    scrivi(f'{d}/principali.json', {'_nota': f'Luoghi principali di {nome}, nell\'ordine di importanza (sono mostrati per primi sulla mappa).', 'luoghi': []})
    scrivi(f'{d}/servizi.json', {'_nota': nota('servizi pratici'), 'servizi': []})
    scrivi(f'{d}/personaggi.json', {'personaggi': []})
    scrivi(f'{d}/storia.json', {'periodi': []})
    scrivi(f'{d}/immagini.json', {'_nota': 'Generato da strumenti/prepara_pacchetto.py: foto presenti in assets/', 'luoghi': {}, 'cibi': [], 'aguzza': []})
    for sotto in ('luoghi', 'cibi', 'aguzza', 'personaggi', 'mappa'):
        os.makedirs(os.path.join(cartella, 'assets', sotto), exist_ok=True)
        open(os.path.join(cartella, 'assets', sotto, '.gitkeep'), 'w').close()
    scrivi(os.path.join(cartella, 'audioguide', 'testi.json'), {'luoghi': {}})

    with open('catalogo.json', encoding='utf-8') as f:
        catalogo = json.load(f)
    catalogo['citta'].append({
        'id': id_citta, 'nome': nome, 'provincia': provincia,
        'motto': {l: '' for l in ('it', 'en', 'fr', 'de', 'es')},
        'stato': 'in_preparazione', 'anteprima': [],
        'pacchetto': None, 'sku': None, 'coordinate': punto,
    })
    with open('catalogo.json', 'w', encoding='utf-8') as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'Creato {cartella}. Ora: luoghi.json, mappa, servizi, mezzi, foto; poi prepara_pacchetto.py.')
    print('Quando è pronta, in catalogo.json: "stato": "disponibile", "motto" nelle 5 lingue e gli indirizzi',
          f'{RADICE}{id_citta}/manifest.json e manifest_prova.json (campi "pacchetto" e "pacchetto_prova").')


main()
