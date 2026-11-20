#!/usr/bin/env python3
"""Aggiunge la tramvia di Firenze (GEST, open data Regione Toscana, CC BY) a autobus.json e orari_autobus.json.

Uso: python3 strumenti/converti_tram_gest.py <cartella_gtfs_gest> <pacchetti/<citta>/dati> [esamina|converti] [festivi]

- Le linee del feed (route_type 0) diventano linee "tram" con id "TRAM-<etichetta>"; le eventuali linee TRAM- già presenti
  vengono sostituite, quelle degli autobus restano.
- Le fermate si agganciano alle fermate di servizi.json entro 60 m, altrimenti "gtfs-<stop_id>".
- Gli orari usano gli stessi giorni (feriale/sabato/festivo) e lo stesso periodo di validità degli orari degli autobus già nel pacchetto.
- "esamina" stampa com'è fatto il feed (linee, direzioni, destinazioni) senza scrivere nulla.
"""
import datetime
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from converti_autobus_at import (AGGANCIO_M, base36, bel_nome, distanza, leggi, minuti, righe, tipo_giorno)  # noqa: E402

GESTORE = 'GEST'
URL_ORARI = 'https://www.at-bus.it/it/viaggia/linee-e-orari/firenze'
COLORE = '#15ac96'


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    gtfs, dati = sys.argv[1], sys.argv[2]
    azione = sys.argv[3] if len(sys.argv) > 3 else 'esamina'
    festivi = set(filter(None, (sys.argv[4] if len(sys.argv) > 4 else '').split(',')))

    routes = {r['route_id']: r for r in leggi(gtfs, 'routes.txt') if r['route_type'] == '0'}
    trips = {t['trip_id']: t for t in leggi(gtfs, 'trips.txt') if t['route_id'] in routes}
    stops = {s['stop_id']: {'nome': bel_nome(s['stop_name']), 'pos': (float(s['stop_lat']), float(s['stop_lon']))}
             for s in leggi(gtfs, 'stops.txt') if s['stop_lat']}
    corse = defaultdict(list)
    for ind, r in righe(gtfs, 'stop_times.txt'):
        t = r[ind['trip_id']]
        if t in trips:
            corse[t].append((int(r[ind['stop_sequence']]), r[ind['stop_id']], minuti(r[ind['departure_time']])))
    for t in corse:
        corse[t].sort()

    date_servizio = defaultdict(set)
    for r in leggi(gtfs, 'calendar_dates.txt'):
        if r['exception_type'] == '1':
            date_servizio[r['service_id']].add(r['date'])

    if azione == 'esamina':
        for rid, rt in routes.items():
            print('LINEA', rt['route_short_name'], rt['route_long_name'], rt.get('route_color'))
            for verso in ('0', '1'):
                c = Counter()
                for t, tr in trips.items():
                    if tr['route_id'] == rid and tr['direction_id'] == verso and t in corse:
                        seq = corse[t]
                        c[(tr['trip_headsign'], stops[seq[0][1]]['nome'], stops[seq[-1][1]]['nome'], len(seq))] += 1
                for k, n in c.most_common(12):
                    print('  verso', verso, n, 'corse', k)
        tutte = sorted({d for v in date_servizio.values() for d in v})
        print('date servizio', tutte[0], tutte[-1], len(tutte))
        return

    esist = json.load(open(os.path.join(dati, 'orari_autobus.json'), encoding='utf-8'))
    bus = json.load(open(os.path.join(dati, 'autobus.json'), encoding='utf-8'))
    da, a = esist['validita']
    serv = json.load(open(os.path.join(dati, 'servizi.json'), encoding='utf-8'))['servizi']
    bus_osm = [s for s in serv if s['tipo'] == 'autobus']

    def aggancia(pos):
        migliore, d_min = None, AGGANCIO_M
        for b in bus_osm:
            d = distanza(pos, (b['lat'], b['lon']))
            if d <= d_min:
                migliore, d_min = b['id'], d
        return migliore

    aggancio = {sid: aggancia(s['pos']) for sid, s in stops.items()}
    id_fermata = lambda sid: aggancio.get(sid) or f'gtfs-{sid}'

    # etichetta: nome breve del feed (es. "T2"); una linea per route
    etichetta = lambda rid: routes[rid]['route_short_name'] or rid
    # via i vecchi tram del pacchetto (e le loro fermate/orari)
    vecchie = {l['id'] for l in bus['linee'] if l['id'].startswith('TRAM-')}
    bus['linee'] = [l for l in bus['linee'] if l['id'] not in vecchie]
    for fid in list(bus['fermate']):
        bus['fermate'][fid]['linee'] = [x for x in bus['fermate'][fid]['linee'] if x not in vecchie]
        if not bus['fermate'][fid]['linee']:
            del bus['fermate'][fid]
    bus['fermataLinee'] = {f: [x for x in v if x not in vecchie] for f, v in bus['fermataLinee'].items()}
    bus['fermataLinee'] = {f: v for f, v in bus['fermataLinee'].items() if v}
    for fid in list(esist['orari']):
        for lid in list(esist['orari'][fid]):
            if lid in vecchie:
                del esist['orari'][fid][lid]
        if not esist['orari'][fid]:
            del esist['orari'][fid]

    nuove = []
    for rid in sorted(routes, key=etichetta):
        rt, lid = routes[rid], f'TRAM-{etichetta(rid)}'
        direzioni = []
        for verso in ('0', '1'):
            ts = [t for t, tr in trips.items() if tr['route_id'] == rid and tr['direction_id'] == verso and t in corse]
            if not ts:
                continue
            migliore = max(ts, key=lambda t: len(corse[t]))
            ids = []
            for _, sid, _ in corse[migliore]:
                fid = id_fermata(sid)
                if fid not in ids:
                    ids.append(fid)
                f = bus['fermate'].setdefault(fid, {'nome': stops[sid]['nome'], 'lat': stops[sid]['pos'][0], 'lon': stops[sid]['pos'][1], 'linee': []})
                if lid not in f['linee']:
                    f['linee'].append(lid)
                if lid not in bus['fermataLinee'].setdefault(fid, []):
                    bus['fermataLinee'][fid].append(lid)
            d = {'direzione': int(verso), 'circolare': False, 'fermate': ids, 'richiesta': []}
            if len(ids) > 1:
                d['titolo'] = f"{bus['fermate'][ids[0]]['nome']} → {bus['fermate'][ids[-1]]['nome']}"
            direzioni.append(d)
        nuove.append({'id': lid, 'etichetta': etichetta(rid), 'mezzo': 'tram',
                      'colore': '#' + rt['route_color'] if rt.get('route_color') else COLORE,
                      'testo': '#' + rt['route_text_color'] if rt.get('route_text_color') else '#000000',
                      'notturna': False, 'gestore': GESTORE, 'pdf': URL_ORARI, 'direzioni': direzioni})
    bus['linee'] = bus['linee'] + nuove

    orari = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(set))))
    for t, seq in corse.items():
        tr = trips[t]
        tipi = {tipo_giorno(d, festivi) for d in date_servizio.get(tr['service_id'], ()) if da <= d <= a}
        if not tipi:
            continue
        lid = f"TRAM-{etichetta(tr['route_id'])}"
        for _, sid, mins in seq:
            fid = id_fermata(sid)
            if lid in bus['fermate'].get(fid, {}).get('linee', []):
                for g in tipi:
                    orari[fid][lid][tr['direction_id']][g].add(mins)
    for fid, per_linea in orari.items():
        for lid, per_verso in per_linea.items():
            out = {}
            for verso, per_g in per_verso.items():
                gruppi = defaultdict(list)
                for g, mins in per_g.items():
                    gruppi[tuple(sorted(mins))].append(g)
                out[verso] = [[sorted(gs), ','.join(base36(m) for m in mins)] for mins, gs in gruppi.items()]
            esist['orari'].setdefault(fid, {})[lid] = out

    nota_t = f' Tramvia: GEST (open data Regione Toscana, CC BY).'
    for d_ in (bus, esist):
        if nota_t not in d_.get('_nota', ''):
            d_['_nota'] = d_.get('_nota', '') + nota_t
    json.dump(bus, open(os.path.join(dati, 'autobus.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(esist, open(os.path.join(dati, 'orari_autobus.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('tram:', [(l['id'], [len(x['fermate']) for x in l['direzioni']]) for l in nuove], 'validità', da, a)


if __name__ == '__main__':
    main()
