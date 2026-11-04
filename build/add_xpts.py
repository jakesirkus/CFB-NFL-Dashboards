"""Box-score expected score (xPts) and deserved win % (xWin) for every game on a dashboard page.
Model = build/xpts_model.json (fixed coefficients, refitted Nov 2 2026 without a turnover term; see its _doc).
Writes boxscores[gk][team].meta.xPts/xWin, games[team][i].xPts/xPtsAllowed/xWin, and meta.xptsModel.
Turnover-neutral drives (Nov 3 2026, model 'availInput' = 'availYardsPctNoTO'): a drive that ENDS in a turnover counts as the better
of what it gained and the team's average drive share in the available-yards share used here (box drives.availYardsPctNoTO, from the drive chart; the displayed Available Yards % is unchanged),
so an interception on the first play of a drive no longer drags the offense's deserved score down. Drive charts: inline (NFL) or
<IN dir>/drivecharts/*.json (CFB).  Fit/compare: fit_xpts.py.

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
AVK = M.get('availInput', 'availYardsPct')
TO = {'Interception', 'Fumble', 'Interception (Pick-6)', 'Fumble (Defensive TD)'}
def avail_noto(drs, pub):
    """available-yards % where a drive that ended in a turnover counts as the BETTER of what it actually gained and the team's
    average share on its other drives (a turnover can't hurt; yards gained before it still count). CFB = pooled yards / available
    yards (published value adjusted with chart yards); NFL = mean of per-drive shares (drives starting >5 yds out)."""
    to = [d for d in drs if d['result'] in TO]
    if not to: return pub
    if LG == 'cfb':
        S = sum(100 - d['spot1'] for d in drs); Y = pub * S / 100
        exS = sum(100 - d['spot1'] for d in to); exY = sum(max(0, d['yards']) for d in to)
        s0 = (Y - exY) / (S - exS) if S - exS > 0 else 0.0
        Y2 = Y - exY + sum(max(max(0, d['yards']), s0 * (100 - d['spot1'])) for d in to)
        return round(max(0.0, 100 * Y2 / S), 1) if S > 0 else 0.0
    av = [d for d in drs if 100 - d['spot1'] > 5]; ok = [d for d in av if d['result'] not in TO]
    if not av: return 0.0
    s0 = sum(d['yards'] / (100 - d['spot1']) for d in ok) / len(ok) if ok else 0.0
    return round(100 * sum(max(d['yards'] / (100 - d['spot1']), s0) if d['result'] in TO else d['yards'] / (100 - d['spot1']) for d in av) / len(av), 1)
def inputs(b):
    return (V(b['drives']['total']) or 0, V(b['drives'].get(AVK, b['drives']['availYardsPct'])) or 0, V(b['overall']['successRate']) or 0,
            V(b['overall']['explosiveRate']) or 0, V(b['turnovers']['ints']) or 0, V(b['turnovers']['fumbleEvents']) or 0)
def xpts(b):
    d, av, sr, ex, ints, fum = inputs(b)
    raw = (C['intercept'] + C['drives'] * d + C['drivesXavail'] * d * av / 100 + C['drivesXsuccess'] * d * sr / 100
           + C.get('drivesXexpl', 0) * d * ex / 100 + C.get('expGiveaways', 0) * (ints + 0.5 * fum))
    return round(max(0.0, raw), 1)
def xwin(a, b): return float(round(100 / (1 + math.exp(-M['winSlope'] * (a - b)))))

s, a, b, D = load(SRC)
if AVK == 'availYardsPctNoTO':                 # fill the turnover-neutral available-yards share from the drive charts
    import glob
    CH = {g: v['driveChart'] for g, v in D['boxscores'].items() if v.get('driveChart')}
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(SRC)), 'drivecharts', '*.json')): CH.update(json.load(open(f)))
    nch = 0
    for gk, v in D['boxscores'].items():
        for t, x in v.items():
            if t == 'driveChart': continue
            pub = V(x['drives']['availYardsPct']) or 0
            drs = [d for d in CH.get(gk) or [] if d['team'] == t and (d.get('plays') or 0) > 0 and d.get('spot1') is not None]
            x['drives']['availYardsPctNoTO'] = avail_noto(drs, pub) if drs else pub; nch += bool(drs)
    print(f'{LG}: turnover-neutral available-yards share on {nch} team-boxes (drive charts found)')
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
