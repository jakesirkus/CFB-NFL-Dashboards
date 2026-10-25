"""Box-score expected score (xPts) and deserved win % (xWin) for every game on a dashboard page.
Model = build/xpts_model.json (fixed coefficients, fitted Oct 25 2026 on Weeks 1-7; see its _doc).
Writes boxscores[gk][team].meta.xPts/xWin, games[team][i].xPts/xPtsAllowed/xWin, and meta.xptsModel.

usage: add_xpts.py cfb|nfl IN.html OUT.html [--recompute gk,gk,...] [--all] [--prev PREV.html]
  default      compute only games that have no xPts yet (new games)
  --recompute  also recompute these games (e.g. after their box score was regenerated)
  --all        recompute every game; with --prev, a game whose model inputs are unchanged from PREV keeps PREV's values
               (so a full NFL rebuild doesn't drift by 0.1 from rounding)"""
import sys, json, math, os
LG, SRC, DST = sys.argv[1:4]; args = sys.argv[4:]
REC = set(args[args.index('--recompute') + 1].split(',')) if '--recompute' in args else set()
ALL = '--all' in args
PREV = args[args.index('--prev') + 1] if '--prev' in args else None
M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xpts_model.json')))[LG]
C = M['coef']; TAG = '<script id="dashboard-data" type="application/json">'

def load(p):
    s = open(p).read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); return s, a, b, json.loads(s[a:b])
def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x
def inputs(b):
    return (V(b['drives']['total']) or 0, V(b['drives']['availYardsPct']) or 0, V(b['overall']['successRate']) or 0,
            V(b['overall']['explosiveRate']) or 0, V(b['turnovers']['ints']) or 0, V(b['turnovers']['fumbleEvents']) or 0)
def xpts(b):
    d, av, sr, ex, ints, fum = inputs(b)
    raw = (C['intercept'] + C['drives'] * d + C['drivesXavail'] * d * av / 100 + C['drivesXsuccess'] * d * sr / 100
           + C.get('drivesXexpl', 0) * d * ex / 100 + C['expGiveaways'] * (ints + 0.5 * fum))
    return round(max(0.0, raw), 1)
def xwin(a, b): return float(round(100 / (1 + math.exp(-M['winSlope'] * (a - b)))))

s, a, b, D = load(SRC)
P = load(PREV)[3]['boxscores'] if PREV else {}
done = kept = 0
for gk, v in D['boxscores'].items():
    ts = [t for t in v if t != 'driveChart']
    if len(ts) != 2: continue
    need = ALL or gk in REC or any('xPts' not in v[t]['meta'] for t in ts)
    if not need: continue
    pv = P.get(gk)
    if ALL and pv and all(t in pv and 'xPts' in pv[t]['meta'] and inputs(pv[t]) == inputs(v[t]) for t in ts):
        for t in ts: v[t]['meta']['xPts'] = pv[t]['meta']['xPts']
        kept += 1
    else:
        for t in ts: v[t]['meta']['xPts'] = xpts(v[t])
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
miss = 0
for t, L in D['games'].items():
    for g in L:
        k = box.get((t, g['week'], g['opp']))
        if k is None: miss += 1; continue
        g['xPts'], g['xPtsAllowed'], g['xWin'] = k
D['meta']['xptsModel'] = M
js = json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
open(DST, 'w').write(s[:a] + js + s[b:])
print(f'{LG} xPts: computed {done} games, kept {kept} unchanged, game-log rows without a box: {miss}')
