#!/usr/bin/env python3
"""Converte il feed GTFS di Autolinee Toscane (Regione Toscana, open data) nel formato del motore
(autobus.json e orari_autobus.json) per le linee urbane di una città.

Uso: python3 strumenti/converti_autobus_at.py <cartella_gtfs> <pacchetti/<citta>/dati> <agency_id> [raggio_m] [festivi]

- <agency_id>: azienda del feed (es. UFI = "at - Firenze urbano").
- Si tengono le linee di quell'azienda che passano entro raggio_m (default 600) da un luogo del pacchetto.
- festivi: date dei giorni festivi infrasettimanali (AAAAMMGG, separate da virgola); in quei giorni valgono gli orari festivi.
- Le fermate GTFS si agganciano alle fermate di servizi.json se sono entro 60 m, altrimenti diventano "gtfs-<stop_id>".
- Il verso di ogni linea è il direction_id del feed; il percorso mostrato è quello della corsa più lunga.
- Orari: feriale, sabato, festivo (domenica e festivi). Il feed copre poche settimane: la validità è scritta nei file.
"""
import csv
import datetime
import json
import math
import os
import re
import sys
from collections import defaultdict

AGGANCIO_M = 60
GESTORE = 'Autolinee Toscane'
URL_ORARI = 'https://www.at-bus.it/it/viaggia/linee-e-orari/firenze'
COLORE_DEFAULT = '#15ac96'
MINUSCOLE = {'di', 'del', 'della', 'dello', 'dei', 'degli', 'delle', 'da', 'dal', 'dalla', 'e', 'a', 'al', 'alla', 'in', 'il', 'la', 'le',
             'lo', 'i', 'gli', 'con', 'per', 'su', 'sul', 'sulla', 'ai', 'alle', 'nel', 'nella'}


def righe(cartella, nome):
    with open(os.path.join(cartella, nome), encoding='utf-8-sig', newline='') as f:
        lettore = csv.reader(f)
        intestazione = next(lettore)
        indice = {c: i for i, c in enumerate(intestazione)}
        for r in lettore:
            yield indice, r


def leggi(cartella, nome):
    return [{c: r[i] if i < len(r) else '' for c, i in ind.items()} for ind, r in righe(cartella, nome)]


def distanza(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def minuti(orario):
    h, m, _ = orario.split(':')
    return int(h) * 60 + int(m)


def base36(n):
    cifre = '0123456789abcdefghijklmnopqrstuvwxyz'
    out = ''
    while True:
        n, r = divmod(n, 36)
        out = cifre[r] + out
        if not n:
            return out


def bel_nome(testo):
    """MAIUSCOLO del feed -> Iniziali Maiuscole (con le preposizioni minuscole)."""
    testo = re.sub(r'\s+', ' ', testo.strip())
    parole = testo.lower().split(' ')
    out = []
    for i, p in enumerate(parole):
        if i > 0 and p in MINUSCOLE:
            out.append(p)
        else:
            out.append(re.sub(r"(^|['’.\-/(])([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), p))
    return ' '.join(out)


def tipo_giorno(data, festivi):
    if data in festivi:
        return 2
    giorno = datetime.datetime.strptime(data, '%Y%m%d').weekday()
    return 2 if giorno == 6 else 1 if giorno == 5 else 0


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    gtfs, dati, agenzia = sys.argv[1], sys.argv[2], sys.argv[3]
    raggio = float(sys.argv[4]) if len(sys.argv) > 4 else 600
    festivi = set(filter(None, (sys.argv[5] if len(sys.argv) > 5 else '').split(',')))

    routes = {r['route_id']: r for r in leggi(gtfs, 'routes.txt') if r['agency_id'] == agenzia and r['route_type'] == '3'}
    trips = {t['trip_id']: t for t in leggi(gtfs, 'trips.txt') if t['route_id'] in routes}
    stops = {}
    for s in leggi(gtfs, 'stops.txt'):
        if s['stop_lat']:
            stops[s['stop_id']] = {'nome': bel_nome(s['stop_name']), 'pos': (float(s['stop_lat']), float(s['stop_lon']))}

    raw = json.load(open(os.path.join(dati, 'luoghi.json'), encoding='utf-8'))
    luoghi = raw if isinstance(raw, list) else raw['luoghi']
    centri = [(l['latitudine'], l['longitudine']) for l in luoghi if l.get('latitudine') is not None]
    vicine = {sid for sid, s in stops.items() if any(distanza(s['pos'], c) <= raggio for c in centri)}
    print('fermate vicine ai luoghi:', len(vicine), ' linee dell\'azienda:', len(routes), ' corse:', len(trips))

    # orari delle corse dell'azienda (un solo passaggio sul file grande)
    corse = defaultdict(list)  # trip_id -> [(seq, stop_id, minuti)]
    for ind, r in righe(gtfs, 'stop_times.txt'):
        t = r[ind['trip_id']]
        if t in trips:
            corse[t].append((int(r[ind['stop_sequence']]), r[ind['stop_id']], minuti(r[ind['departure_time']])))

    rotte = {trips[t]['route_id'] for t, seq in corse.items() if any(sid in vicine for _, sid, _ in seq)}
    print('linee vicine:', sorted((routes[r]['route_short_name'] for r in rotte), key=lambda e: (len(e), e)))

    # date di servizio (il feed usa solo aggiunte in calendar_dates.txt)
    date_servizio = defaultdict(set)
    for r in leggi(gtfs, 'calendar_dates.txt'):
        if r['exception_type'] == '1':
            date_servizio[r['service_id']].add(r['date'])
    usate = {d for t in trips.values() if t['route_id'] in rotte for d in date_servizio.get(t['service_id'], ())}
    validita = [min(usate), max(usate)]

    servizi = json.load(open(os.path.join(dati, 'servizi.json'), encoding='utf-8'))['servizi']
    bus_osm = [s for s in servizi if s['tipo'] == 'autobus']
    aggancio = {}
    for sid, s in stops.items():
        migliore, d_min = None, AGGANCIO_M
        for a in bus_osm:
            d = distanza(s['pos'], (a['lat'], a['lon']))
            if d <= d_min:
                migliore, d_min = a['id'], d
        aggancio[sid] = migliore

    def id_fermata(sid):
        return aggancio.get(sid) or f'gtfs-{sid}'

    def etichetta(rid):
        return routes[rid]['route_short_name'] or rid

    linee_out, fermate_out, fermata_linee = [], {}, defaultdict(list)
    for rid in sorted(rotte, key=lambda r: (len(etichetta(r)), etichetta(r))):
        rt, lid = routes[rid], f"AUT-{etichetta(rid)}"
        direzioni = []
        for verso in ('0', '1'):
            ts = [t for t, tr in trips.items() if tr['route_id'] == rid and tr['direction_id'] == verso and t in corse]
            if not ts:
                continue
            migliore = max(ts, key=lambda t: len(corse[t]))
            ids = []
            for _, sid, _ in sorted(corse[migliore]):
                if sid not in stops:
                    continue
                fid = id_fermata(sid)
                if fid not in ids:
                    ids.append(fid)
                f = fermate_out.setdefault(fid, {'nome': stops[sid]['nome'], 'lat': stops[sid]['pos'][0], 'lon': stops[sid]['pos'][1], 'linee': []})
                if lid not in f['linee']:
                    f['linee'].append(lid)
                if lid not in fermata_linee[fid]:
                    fermata_linee[fid].append(lid)
            d = {'direzione': int(verso), 'circolare': False, 'fermate': ids, 'richiesta': []}
            if len(ids) > 1:
                d['titolo'] = f"{fermate_out[ids[0]]['nome']} → {fermate_out[ids[-1]]['nome']}"
            direzioni.append(d)
        linee_out.append({
            'id': lid, 'etichetta': etichetta(rid), 'mezzo': 'autobus',
            'colore': '#' + rt['route_color'] if rt.get('route_color') else COLORE_DEFAULT,
            'testo': '#' + rt['route_text_color'] if rt.get('route_text_color') else '#FFFFFF',
            'notturna': False, 'gestore': GESTORE, 'pdf': URL_ORARI, 'direzioni': direzioni,
        })

    # orari per fermata, linea, verso e tipo di giorno (solo le fermate usate dalle linee)
    orari = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(set))))
    for t, seq in corse.items():
        tr = trips[t]
        if tr['route_id'] not in rotte:
            continue
        tipi = {tipo_giorno(d, festivi) for d in date_servizio.get(tr['service_id'], ())}
        if not tipi:
            continue
        lid = f"AUT-{etichetta(tr['route_id'])}"
        for _, sid, mins in seq:
            fid = id_fermata(sid)
            if fid in fermate_out and lid in fermate_out[fid]['linee']:
                for g in tipi:
                    orari[fid][lid][tr['direction_id']][g].add(mins)
    orari_out = {}
    for fid, per_linea in orari.items():
        orari_out[fid] = {}
        for lid, per_verso in per_linea.items():
            orari_out[fid][lid] = {}
            for verso, per_g in per_verso.items():
                gruppi = defaultdict(list)
                for g, mins in per_g.items():
                    gruppi[tuple(sorted(mins))].append(g)
                orari_out[fid][lid][verso] = [[sorted(gs), ','.join(base36(m) for m in mins)] for mins, gs in gruppi.items()]

    # i festivi infrasettimanali nel periodo: valgono gli orari festivi (servizio 2)
    date = {}
    for d in sorted(festivi):
        if validita[0] <= d <= validita[1]:
            giorno = datetime.datetime.strptime(d, '%Y%m%d').weekday()
            if giorno < 6:
                date[d] = {'piu': [2], 'meno': [0] if giorno < 5 else [1]}
    servizi_out = [{'giorni': '1111100', 'da': validita[0], 'a': validita[1]},
                   {'giorni': '0000010', 'da': validita[0], 'a': validita[1]},
                   {'giorni': '0000001', 'da': validita[0], 'a': validita[1]}]
    fmt = lambda d: f'{d[6:]}/{d[4:6]}/{d[:4]}'
    nota = (f'Orari programmati {GESTORE} (open data Regione Toscana, feed GTFS), feriale, sabato e festivo, '
            f'dal {fmt(validita[0])} al {fmt(validita[1])}. Generato da strumenti/converti_autobus_at.py. Verificare sul sito {GESTORE}.')
    json.dump({'_nota': nota, 'validita': validita, 'linee': linee_out,
               'fermate': fermate_out, 'fermataLinee': dict(fermata_linee)},
              open(os.path.join(dati, 'autobus.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({'_nota': nota, 'validita': validita, 'servizi': servizi_out, 'date': date, 'capolinea': [], 'orari': orari_out},
              open(os.path.join(dati, 'orari_autobus.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'linee: {len(linee_out)}, fermate: {len(fermate_out)}, fermate con orari: {len(orari_out)}, validità {validita[0]}-{validita[1]}')


if __name__ == '__main__':
    main()
