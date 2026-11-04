"""Grid test of NFL deserved-score designs on 10 seasons (2016-2025), leave-one-season-out.
Inputs: FEAT.pkl (nfl_hist_features.py: points, drives, success rate, explosive rate, garbage shifts) + CAP.pkl (nfl_capped_yards.py:
per-drive yards with each play's gain capped). Available-yards share is rebuilt from the capped drive yards:
  per drive min(yards/start-to-goal, 1) (drives starting >5 yds out); a drive that ends in a turnover counts as the better of its own share
  and s0 = (team's clean-drive shares + k * league average) / (clean drives + k)   [k=0 team average, k=inf league average]
Forms: 'A+S' avail + success, 'A+S+E' + explosive rate, 'S+E' success + explosive only (pure down-to-down). All x drives.
Garbage: drives/plays faded by win probability (wp90_98 = full weight up to 90%, none at 98%).
Score: forward prediction (team's average deserved margin in earlier games that season vs the opponent's -> next game's margin, wk 5+).
usage: nfl_xpts_grid.py FEAT.pkl CAP.pkl"""
import sys, itertools, numpy as np, pandas as pd
F = pd.read_pickle(sys.argv[1]); CAP = pd.read_pickle(sys.argv[2])
F = F[F.dr > 0].reset_index(drop=True)
LEAGUE = None
def wfun(wp, lo, hi):
    lead = np.maximum(wp, 1 - wp)
    return (lead < hi).astype(float) if hi <= lo else np.clip((hi - lead) / (hi - lo), 0, 1)
GSPEC = {'none': None, 'wp90_98': (0.90, 0.98), 'wp95hard': (0.95, 0.95)}
DR = {k: g for k, g in CAP.groupby(['game_id', 'posteam'], sort=False)}
idx = [DR.get((r.gk, r.t)) for r in F.itertuples()]
ok = np.array([d is not None for d in idx]); print('team-games with capped drives:', ok.sum(), 'of', len(F))
F = F[ok].reset_index(drop=True); idx = [d for d in idx if d is not None]

def avail(capcol, k, garb):
    yc = 'y' if capcol is None else capcol
    allsh = np.concatenate([np.minimum(d[yc].values / d.ytg.values, 1)[(d.ytg.values > 5) & ~d.to.values.astype(bool)] for d in idx])
    L = allsh.mean(); out = np.zeros(len(idx))
    for i, d in enumerate(idx):
        m = d.ytg.values > 5
        if not m.any(): continue
        sh = np.minimum(d[yc].values[m] / d.ytg.values[m], 1); to = d.to.values[m].astype(bool)
        if k is not None and to.any():
            cl = sh[~to]; s0 = (cl.sum() + (0 if k == 0 else k) * L) / (len(cl) + k) if (len(cl) + k) > 0 else L
            if k == np.inf: s0 = L
            sh = np.where(to, np.maximum(sh, s0), sh)
        w = np.ones(len(sh)) if GSPEC[garb] is None else wfun(d.wp.fillna(0.5).values[m], *GSPEC[garb])
        if GSPEC[garb] is not None:                  # competitive drives, blended toward all drives with 6 drives of weight
            full = sh.mean(); comp = np.average(sh, weights=w) if w.sum() > 0 else full
            out[i] = 100 * (full + w.sum() / (w.sum() + 6) * (comp - full))
        else: out[i] = 100 * sh.mean()
    return out

def design(av, form, garb):
    sr = F.sr.values + (F[f'{garb}_ds'].fillna(0).values if garb != 'none' else 0)
    ex = F.ex.values + (F[f'{garb}_de'].fillna(0).values if garb != 'none' else 0)
    cols = [np.ones(len(F)), F.dr.values]
    if 'A' in form: cols.append(F.dr.values * av / 100)
    cols.append(F.dr.values * sr / 100)
    if 'E' in form: cols.append(F.dr.values * ex / 100)
    return np.column_stack(cols)

def forward(xp):
    d = F[['season', 'week', 'gk', 't', 'o', 'home', 'pts', 'opts', 'spread']].assign(x=xp)
    g = d.merge(d[['gk', 't', 'x']].rename(columns={'t': 'o', 'x': 'xo'}), on=['gk', 'o'])
    g['dm'] = g.x - g.xo; g['am'] = g.pts - g.opts; g = g.sort_values(['season', 'week'])
    rows = []
    for s, gs in g.groupby('season'):
        hist = {}
        for wk, gw in gs.groupby('week'):
            for r in gw.itertuples():
                if r.home and len(hist.get(r.t, [])) >= 4 and len(hist.get(r.o, [])) >= 4:
                    rows.append((np.mean(hist[r.t]) - np.mean(hist[r.o]), r.am, r.spread))
            for r in gw.itertuples(): hist.setdefault(r.t, []).append(r.dm)
    R = np.array(rows, float); A = np.c_[np.ones(len(R)), R[:, 0]]
    b = np.linalg.lstsq(A, R[:, 1], rcond=None)[0]
    return np.abs(A @ b - R[:, 1]), R

def run(av, form, garb):
    X = design(av, form, garb); y = F.pts.values.astype(float); xp = np.zeros(len(F)); seasons = F.season.values
    for s in np.unique(seasons):
        tr = seasons != s; b = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]; xp[~tr] = np.maximum(0, X[~tr] @ b)
    bfull = np.linalg.lstsq(X, y, rcond=None)[0]
    err, R = forward(xp)
    return xp, err, bfull

res = []
CAPS = [None, 'c15', 'c20', 'c25', 'c30', 'c40']; KS = [None, 0, 4, np.inf]
cache = {}
for garb in ('none', 'wp90_98', 'wp95hard'):
    for cap, k in itertools.product(CAPS, KS):
        av = avail(cap, k, garb)
        for form in ('A+S', 'A+S+E'):
            xp, err, b = run(av, form, garb)
            res.append(dict(garb=garb, cap=cap or 'none', turnover={None: 'none', 0: 'team avg', 4: 'blend k4', np.inf: 'league avg'}[k], form=form,
                            fitMAE=np.mean(np.abs(xp - F.pts.values)), fwdMAE=err.mean(), _err=err, coef=np.round(b, 3).tolist()))
    xp, err, b = run(None, 'S+E', garb)
    res.append(dict(garb=garb, cap='-', turnover='-', form='S+E', fitMAE=np.mean(np.abs(xp - F.pts.values)), fwdMAE=err.mean(), _err=err, coef=np.round(b, 3).tolist()))
# current site formula analogue: no cap, team-average turnover rule, A+S, no garbage
base = [r for r in res if r['garb'] == 'none' and r['cap'] == 'none' and r['turnover'] == 'team avg' and r['form'] == 'A+S'][0]['_err']
for r in res:
    d = r['_err'] - base; bs = [d[np.random.default_rng(i).integers(0, len(d), len(d))].mean() for i in range(500)]
    r['vsSite'] = round(float(d.mean()), 3); r['pBetter'] = round(float(np.mean(np.array(bs) < 0)), 2)
T = pd.DataFrame([{k: v for k, v in r.items() if k != '_err'} for r in res]).sort_values('fwdMAE')
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60)
print(T.head(30).round(3).to_string(index=False)); print('...'); print(T.tail(5).round(3).to_string(index=False))
T.to_pickle(sys.argv[1].replace('.pkl', '_grid.pkl'))
err, R = forward(F.pts.values.astype(float)); v = ~np.isnan(R[:, 2])
print(f'\nbenchmarks: actual points {err.mean():.3f} | Vegas spread {np.mean(np.abs(R[v, 2] - R[v, 1])):.3f} (n={v.sum()}) | games scored {len(err)}')
