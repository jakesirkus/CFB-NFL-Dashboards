"""Projected score / total for the Matchup tab: fits totals_model.py on every game on the page and writes DATA.meta.totals
(points-per-drive offense/defense ratings, possessions (pace) ratings, home edge, rating anchor, walk-forward backtest summary).
Settings (Nov 2 2026 backtests): points basis = box-score expected points per drive (w = 0), shrinkage CFB (32, 16), NFL (32, 64);
CFB: games vs FCS weighted 5% and FCS floored at the worst FBS unit; anchored to the user's power ratings (ratings/cfb.json, blend
25% at-the-time / 75% current, like opp_adjust) - margins MAE 13.2 -> 12.1 with the same total accuracy; walk-forward bias correction.
Run after add_xpts.py. Idempotent.  usage: add_totals.py cfb|nfl IN.html OUT.html"""
import sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import totals_model as TM
LG, SRC, DST = sys.argv[1:4]
CFG = {'cfb': dict(w=0.0, lam=(32, 16)), 'nfl': dict(w=0.0, lam=(32, 64))}[LG]
FW = 0.05 if LG == 'cfb' else 1.0          # user (Nov 2): games vs FCS should barely move the ratings
BLEND = 0.25
s = open(SRC).read(); a = s.index(TM.TAG) + len(TM.TAG); b = s.index('</script>', a); D = json.loads(s[a:b])
G, teams = TM.load(LG, D)
FBS = set(teams) if LG == 'cfb' else None
RF = os.path.join(HERE, f'ratings/{LG}.json')
RT = json.load(open(RF))['teams'] if os.path.exists(RF) else None      # private, git-ignored; without it the model runs unanchored

def rating_asof(t, wk):                  # the user's rating going into week wk
    r = RT.get(t) if RT else None
    if not r: return None
    ks = [int(k) for k in r['wk'] if int(k) <= wk - 1]
    return r['wk'][str(max(ks))] if ks else r['wk'][min(r['wk'], key=int)]
def make_rfun(now_wk):                   # ratings as known before week now_wk (None = current), centered on the FBS mean
    cur = (lambda t: (RT[t]['current'] if t in RT else None)) if now_wk is None else (lambda t: rating_asof(t, now_wk))
    vals = [cur(t) for t in teams if cur(t) is not None]; mean = float(np.mean(vals)) if vals else 0.0
    def rf(t, g):
        c = cur(t)
        if c is None: return None
        then = rating_asof(t, g['week']); then = c if then is None else then
        return BLEND * then + (1 - BLEND) * c - mean
    return rf, (lambda t: None if cur(t) is None else cur(t) - mean)

def fit_all(games, now_wk=None):
    if RT is None or LG != 'cfb':
        P = TM.fit(games, CFG['w'], *CFG['lam'], fbs=FBS, fcs_w=FW); rnow = lambda t: None
    else:
        rf, rnow = make_rfun(now_wk)
        P = TM.fit_rated(games, CFG['w'], *CFG['lam'], FBS, FW, rf)
        P['h'] = TM.fit_rated([g for g in games if g['fbs']], CFG['w'], *CFG['lam'], FBS, FW, rf)['h']   # home edge from FBS-vs-FBS games
    if LG == 'cfb':                      # FCS = the worst possible opponent
        P['fcsDef'] = max(P['fcsDef'], max(P['dfn'][t] for t in FBS if t in P['dfn']))
        P['fcsOff'] = min(P['fcsOff'], min(P['off'][t] for t in FBS if t in P['off']))
    return P, rnow

P, rnow = fit_all(G)
# walk-forward backtest with the same settings (each week predicted from earlier weeks and ratings known then)
out = []
for wk in sorted({g['week'] for g in G}):
    if wk < 4: continue
    Pw, rw = fit_all([g for g in G if g['week'] < wk], now_wk=wk)
    Pw['calib'] = float(np.mean([r - x for _, x, _, r, _, _ in out])) if out else 0.0     # bias known at that time
    for g in G:
        if g['week'] != wk or (LG == 'cfb' and not g['fbs']) or g['home'] not in Pw['off'] or g['away'] not in Pw['off']: continue
        h, a_, _ = TM.project(Pw, g['home'], g['away'], g['neutral'], rw(g['home']) or 0.0, rw(g['away']) or 0.0)
        out.append((h + a_, g['ph'] + g['pa'], g['vegas'], h + a_ + Pw['calib'], h - a_, g['ph'] - g['pa']))
o = np.array([(m, x, v if v is not None else np.nan, mm, am) for m, x, v, _, mm, am in out], float)
P['calib'] = float(np.mean([raw - x for _, x, _, raw, _, _ in out])) if out else 0.0
vv = ~np.isnan(o[:, 2])
bt = {'games': int(len(o)), 'mae': round(float(np.mean(np.abs(o[:, 0] - o[:, 1]))), 2) if len(o) else None,
      'vegasGames': int(vv.sum()), 'vegasMae': round(float(np.mean(np.abs(o[vv, 2] - o[vv, 1]))), 2) if vv.any() else None,
      'modelMaeSameGames': round(float(np.mean(np.abs(o[vv, 0] - o[vv, 1]))), 2) if vv.any() else None,
      'bias': round(float(np.mean(o[:, 0] - o[:, 1])), 2) if len(o) else None,
      'marginMae': round(float(np.mean(np.abs(o[:, 3] - o[:, 4]))), 2) if len(o) else None,
      'winnerPct': round(float(100 * np.mean((o[:, 3] > 0) == (o[:, 4] > 0))), 1) if len(o) else None}
keep = [t for t in teams if t in P['off']]
D['meta']['totals'] = {'mu': round(P['mu'], 4), 'h': round(P['h'], 4), 'muD': round(P['muD'], 3), 'w': CFG['w'], 'calib': round(P['calib'], 3),
                       'bO': round(P.get('bO', 0.0), 5), 'bD': round(P.get('bD', 0.0), 5), 'fcsWeight': FW,
                       'ratingsAnchor': bool(RT is not None and LG == 'cfb'),
                       'teams': {t: [round(P['off'][t], 4), round(P['dfn'][t], 4), round(P['pace'][t], 3), round(rnow(t) or 0.0, 3)] for t in keep},
                       'backtest': bt,
                       'note': 'Projected score = (projected possessions / 2) x expected points per drive: your power ratings set overall strength, '
                               'box-score deserved points per drive split it into offense vs defense; possessions from both teams\' pace.'}
open(DST, 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b:])
print(f'{LG} totals: {len(keep)} teams | home edge {P["h"]:+.3f} pts/drive | rating anchor bO {P.get("bO", 0):+.4f} bD {P.get("bD", 0):+.4f} | backtest {bt}')
