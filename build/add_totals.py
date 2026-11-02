"""Projected score / total for the Matchup tab: fits totals_model.py on every game on the page and writes DATA.meta.totals
(points-per-drive offense/defense ratings, possessions (pace) ratings, home edge, plus the walk-forward backtest summary).
Settings chosen by the Nov 2 2026 backtest: points basis = box-score expected points per drive (w = 0; blends with actual
points tested worse), shrinkage CFB (32, 16), NFL (32, 64). Run after add_xpts.py. Idempotent.
usage: add_totals.py cfb|nfl IN.html OUT.html"""
import sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import totals_model as TM
LG, SRC, DST = sys.argv[1:4]
CFG = {'cfb': dict(w=0.0, lam=(32, 16)), 'nfl': dict(w=0.0, lam=(32, 64))}[LG]
s = open(SRC).read(); a = s.index(TM.TAG) + len(TM.TAG); b = s.index('</script>', a); D = json.loads(s[a:b])
G, teams = TM.load(LG, D)
P = TM.fit(G, CFG['w'], *CFG['lam'])
# CFB home edge from FBS-vs-FBS games only (cupcake home games vs FCS inflate it: 0.33 vs 0.20 pts/drive on Nov 2; the backtest
# margin error is lowest near the FBS-only value)
if LG == 'cfb': P['h'] = TM.fit([g for g in G if g['fbs']], CFG['w'], *CFG['lam'])['h']
# walk-forward backtest with the same settings (each week predicted from earlier weeks only)
out = []
for wk in sorted({g['week'] for g in G}):
    if wk < 4: continue
    Pw = TM.fit([g for g in G if g['week'] < wk], CFG['w'], *CFG['lam'])
    if LG == 'cfb': Pw['h'] = TM.fit([g for g in G if g['week'] < wk and g['fbs']], CFG['w'], *CFG['lam'])['h']
    for g in G:
        if g['week'] != wk or (LG == 'cfb' and not g['fbs']) or g['home'] not in Pw['off'] or g['away'] not in Pw['off']: continue
        h, a_, _ = TM.project(Pw, g['home'], g['away'], g['neutral'])
        out.append((h + a_, g['ph'] + g['pa'], g['vegas']))
o = np.array([(m, x, v if v is not None else np.nan) for m, x, v in out], float)
vv = ~np.isnan(o[:, 2])
bt = {'games': int(len(o)), 'mae': round(float(np.mean(np.abs(o[:, 0] - o[:, 1]))), 2) if len(o) else None,
      'vegasGames': int(vv.sum()), 'vegasMae': round(float(np.mean(np.abs(o[vv, 2] - o[vv, 1]))), 2) if vv.any() else None,
      'modelMaeSameGames': round(float(np.mean(np.abs(o[vv, 0] - o[vv, 1]))), 2) if vv.any() else None}
keep = [t for t in teams if t in P['off']]
D['meta']['totals'] = {'mu': round(P['mu'], 4), 'h': round(P['h'], 4), 'muD': round(P['muD'], 3), 'w': CFG['w'],
                       'teams': {t: [round(P['off'][t], 4), round(P['dfn'][t], 4), round(P['pace'][t], 3)] for t in keep},
                       'backtest': bt,
                       'note': 'Projected score = (projected possessions / 2) x opponent-adjusted expected points per drive (box-score deserved score, '
                               'so turnovers, return TDs and red-zone luck are stripped out). Possessions = both teams\' pace.'}
open(DST, 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b:])
top = sorted(keep, key=lambda t: -P['off'][t])[:3]
print(f'{LG} totals: {len(keep)} teams | home edge {P["h"]:+.3f} pts/drive | backtest {bt}')
