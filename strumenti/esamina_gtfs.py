#!/usr/bin/env python3
"""Stampa com'è fatto un feed GTFS e quali linee passano entro RAGGIO metri dai luoghi di un pacchetto.

Uso: python3 strumenti/esamina_gtfs.py <cartella_gtfs> <pacchetti/<citta>/dati/luoghi.json> [raggio_m]
"""
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict


def leggi(cartella, nome):
    p = os.path.join(cartella, nome)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def distanza(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def main():
    g, luoghi_path = sys.argv[1], sys.argv[2]
    raggio = float(sys.argv[3]) if len(sys.argv) > 3 else 400
    for nome in sorted(os.listdir(g)):
        n = sum(1 for _ in open(os.path.join(g, nome), encoding='utf-8-sig')) - 1
        print(f'{nome}: {n} righe')
    ag = leggi(g, 'agency.txt'); print('AGENZIE', [(a.get('agency_id'), a.get('agency_name')) for a in ag][:20])
    cal = leggi(g, 'calendar.txt'); cd = leggi(g, 'calendar_dates.txt')
    print('calendar.txt', len(cal), cal[:2]); print('calendar_dates.txt', len(cd), Counter(r['exception_type'] for r in cd), cd[:2])
    if cal:
        print('validità calendar', min(r['start_date'] for r in cal), max(r['end_date'] for r in cal))
    if cd:
        print('date calendar_dates', min(r['date'] for r in cd), max(r['date'] for r in cd))
    routes = {r['route_id']: r for r in leggi(g, 'routes.txt')}
    print('ROUTES', len(routes), list(routes.values())[:3])
    trips = leggi(g, 'trips.txt'); print('TRIPS', len(trips), trips[:2]); print('direction_id', Counter(t.get('direction_id') for t in trips))
    stops = {s['stop_id']: s for s in leggi(g, 'stops.txt')}; print('STOPS', len(stops), list(stops.values())[:2])
    raw = json.load(open(luoghi_path, encoding='utf-8')); luoghi = raw if isinstance(raw, list) else raw['luoghi']
    centri = [(l['latitudine'], l['longitudine']) for l in luoghi if l.get('latitudine') is not None]
    vicine = {sid for sid, s in stops.items() if s.get('stop_lat') and any(distanza((float(s['stop_lat']), float(s['stop_lon'])), c) <= raggio for c in centri)}
    print('fermate vicine ai luoghi:', len(vicine))
    trip_route = {t['trip_id']: t['route_id'] for t in trips}
    linee = defaultdict(set)
    for r in leggi(g, 'stop_times.txt'):
        if r['stop_id'] in vicine and r['trip_id'] in trip_route:
            linee[trip_route[r['trip_id']]].add(r['stop_id'])
    per_etichetta = Counter()
    for rid in linee:
        r = routes.get(rid, {})
        per_etichetta[(r.get('route_short_name'), r.get('agency_id'), r.get('route_type'))] += 1
    print('LINEE VICINE', len(linee))
    for (e, a, t), k in sorted(per_etichetta.items(), key=lambda x: str(x[0][0])):
        print(f'  {e!r} agenzia={a} tipo={t} route_id={k}')


if __name__ == '__main__':
    main()
