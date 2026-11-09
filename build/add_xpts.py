"""Box-score expected (deserved) score (xPts) and deserved win % (xWin) for every game on a dashboard page.
Model = build/xpts_model.json, VERSION 4 (v3 + yards per play capped at 30 yds/play, Nov 8 2026); originally VERSION 3 (Nov 3 2026, the user's 'option 4'; see its _doc and xpts_v3.py):
  success rate is the core; explosive plays rewarded (explosive-rate term) but each play counts at most 20 yards toward the
  available-yards share (long TDs partly variance); a drive ending in a turnover counts exactly what it gained (like a punt);
  garbage time faded out (NFL win probability / CFB score margin by quarter).
Writes boxscores[gk][team].meta.xPts/xWin, box xptsInputs {av, sr, ex}, games[team][i].xPts/xPtsAllowed/xWin, meta.xptsModel.
Play-by-play: NFL --pbp PBP.pkl|parquet (required); CFB reads cfb_full/prepped_to.pkl (garbage_time.py).

usage: add_xpts.py cfb|nfl IN.html OUT.html [--pbp PBP] [--recompute gk,gk,...] [--all] [--prev PREV.html]
  default      compute only games that have no xPts yet (new games)
  --recompute  also recompute these games (e.g. after their box score was regenerated)
  --all        recompute every game; with --prev, a game whose model inputs are unchanged from PREV keeps PREV's values"""
import sys, json, math, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import xpts_v3
LG, SRC, DST = sys.argv[1:4]; args = sys.argv[4:]
REC = set(args[args.index('--recompute') + 1].split(',')) if '--recompute' in args else set()
ALL = '--all' in args
PREV = args[args.index('--prev') + 1] if '--prev' in args else None
PBP = args[args.index('--pbp') + 1] if '--pbp' in args else None
M = json.load(open(os.path.join(HERE, 'xpts_model.json')))[LG]
assert M.get('version') in (3, 4), 'xpts_model.json is not version 3/4'
C = M['coef']; TAG = '<script id="dashboard-data" type="application/json">'
if LG == 'nfl' and not PBP: sys.exit('NFL needs --pbp PBP.pkl')

def load(p):
    s = open(p).read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); return s, a, b, json.loads(s[a:b])
def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x
def xpts(dr, inp):
    raw = (C['intercept'] + C['drives'] * dr + C['drivesXavail'] * dr * inp['av'] / 100 + C['drivesXsuccess'] * dr * inp['sr'] / 100
           + C['drivesXexpl'] * dr * inp['ex'] / 100 + C.get('drivesXypp', 0.0) * dr * inp.get('ypp', 0.0) / 10)
    return round(max(0.0, raw), 1)
def xwin(a, b): return float(round(100 / (1 + math.exp(-M['winSlope'] * (a - b)))))

s, a, b, D = load(SRC)
I = xpts_v3.inputs(LG, D, M, PBP)
miss = 0
for gk, v in D['boxscores'].items():
    for t, x in v.items():
        if t == 'driveChart': continue
        x['drives'].pop('availYardsPctNoTO', None); x.pop('xptsGarbageAdj', None)      # earlier versions' fields
        z = I.get((gk, t))
        if z is None:
            miss += 1; z = {'av': V(x['drives']['availYardsPct']) or 0, 'dsr': 0.0, 'dex': 0.0}
        x['xptsInputs'] = {'av': round(z['av'], 1), 'sr': round((V(x['overall']['successRate']) or 0) + z['dsr'], 2),
                           'ex': round((V(x['overall']['explosiveRate']) or 0) + z['dex'], 2)}
        if 'ypp' in z: x['xptsInputs']['ypp'] = round(z['ypp'], 3)
P = load(PREV)[3]['boxscores'] if PREV else {}
done = kept = 0
for gk, v in D['boxscores'].items():
    ts = [t for t in v if t != 'driveChart']
    if len(ts) != 2: continue
    need = ALL or gk in REC or any('xPts' not in v[t]['meta'] for t in ts)
    if not need: continue
    pv = P.get(gk)
    if ALL and pv and all(t in pv and 'xPts' in pv[t]['meta'] and pv[t].get('xptsInputs') == v[t]['xptsInputs']
                          and pv[t]['drives']['total'] == v[t]['drives']['total'] for t in ts):
        for t in ts: v[t]['meta']['xPts'] = pv[t]['meta']['xPts']
        kept += 1
    else:
        for t in ts: v[t]['meta']['xPts'] = xpts(V(v[t]['drives']['total']) or 0, v[t]['xptsInputs'])
        done += 1
    t1, t2 = ts
    v[t1]['meta']['xWin'] = xwin(v[t1]['meta']['xPts'], v[t2]['meta']['xPts'])
    v[t2]['meta']['xWin'] = xwin(v[t2]['meta']['xPts'], v[t1]['meta']['xPts'])
# game logs follow the box scores
box = {}
for gk, v in D['boxscores'].items():
    for t, x in v.items():
        if t != 'driveChart' and 'xPts' in x['meta']:
            box[(t, x['meta']['week'], x['meta']['opp'])] = (x['meta']['xPts'], v[x['meta']['opp']]['meta']['xPts'], x['meta']['xWin'])
lmiss = 0
for t, L in D['games'].items():
    for g in L:
        k = box.get((t, g['week'], g['opp']))
        if k is None: lmiss += 1; continue
        g['xPts'], g['xPtsAllowed'], g['xWin'] = k
D['meta']['xptsModel'] = M
js = json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
open(DST, 'w').write(s[:a] + js + s[b:])
print(f'{LG} xPts v{M["version"]}: computed {done} games, kept {kept} unchanged, team-boxes without play-by-play inputs: {miss}, game-log rows without a box: {lmiss}')
