"""Compare NFL deserved-score formulas on 10 past seasons (nfl_hist_features.py output).
Each formula: points = f(drives x rates), fitted leave-one-season-out (fit on 9 seasons, score the 10th).
Scores: fit MAE (how well it explains that game's points) and FORWARD prediction: a team's average deserved margin in its earlier
games that season (minus the opponent's, + home) predicting the next game's actual margin, weeks 5+ (MAE, and vs Vegas spread).
usage: nfl_xpts_eval.py FEAT.pkl"""
import sys, numpy as np, pandas as pd
F = pd.read_pickle(sys.argv[1])
F = F[(F.dr > 0)].copy()
GARB = ['none', 'wp95hard', 'wp90_98', 'wp95_99', 'wp85_95']
FORMS = {
    'current (avail+success)':          ['av', 'sr'],
    '+ explosive':                      ['av', 'sr', 'ex'],
    '+ yards/play':                     ['av', 'sr', 'ypp'],
    '+ EPA/play':                       ['av', 'sr', 'epa'],
    '+ explosive + yards/play':         ['av', 'sr', 'ex', 'ypp'],
    'avail + yards/play + success':     ['av', 'ypp', 'sr'],
}
SCALE = {'av': 100, 'sr': 100, 'ex': 100, 'ypp': 10, 'epa': 1}
SH = {'sr': 'ds', 'ex': 'de', 'av': 'da', 'ypp': 'dy', 'epa': 'dp'}

def design(df, cols, garb):
    X = [np.ones(len(df)), df.dr.values]
    for c in cols:
        v = (df.avnoto if c == 'av' else df[c]).values.astype(float)
        if garb != 'none': v = v + df[f'{garb}_{SH[c]}'].fillna(0).values * (1 if c not in ('ypp', 'epa') else 1)
        X.append(df.dr.values * v / SCALE[c])
    return np.column_stack(X)

def forward(df, xp):
    d = df.assign(x=xp)
    g = d.merge(d[['gk', 't', 'x']].rename(columns={'t': 'o', 'x': 'xo'}), on=['gk', 'o'])
    g['dm'] = g.x - g.xo; g['am'] = g.pts - g.opts
    g = g.sort_values(['season', 'week'])
    rows = []
    for s, gs in g.groupby('season'):
        hist = {}
        for wk, gw in gs.groupby('week'):
            for r in gw.itertuples():
                if r.home and len(hist.get(r.t, [])) >= 4 and len(hist.get(r.o, [])) >= 4:
                    rows.append((np.mean(hist[r.t]) - np.mean(hist[r.o]), r.am, r.spread))
            for r in gw.itertuples(): hist.setdefault(r.t, []).append(r.dm)
    R = np.array(rows, float); A = np.c_[np.ones(len(R)), R[:, 0]]
    b = np.linalg.lstsq(A, R[:, 1], rcond=None)[0]; err = np.abs(A @ b - R[:, 1])
    return err, R

res = []
for garb in GARB:
    for name, cols in FORMS.items():
        if garb != 'none' and name not in ('current (avail+success)', '+ explosive', '+ yards/play', '+ explosive + yards/play'): continue
        xp = np.zeros(len(F)); fitmae = []
        for s in sorted(F.season.unique()):
            tr, te = F.season != s, F.season == s
            Xtr, Xte = design(F[tr], cols, garb), design(F[te], cols, garb)
            b = np.linalg.lstsq(Xtr, F[tr].pts.values, rcond=None)[0]
            xp[te.values] = np.maximum(0, Xte @ b)
        fitmae = np.mean(np.abs(xp - F.pts.values))
        err, R = forward(F, xp)
        res.append(dict(garbage=garb, formula=name, fitMAE=round(fitmae, 3), fwdMAE=round(err.mean(), 3), n=len(err), _err=err))
base = res[0]['_err']
for r in res:
    d = r['_err'] - base; bs = [d[np.random.default_rng(i).integers(0, len(d), len(d))].mean() for i in range(1000)]
    r['vsCurrent'] = round(d.mean(), 3); r['pBetter'] = round(float(np.mean(np.array(bs) < 0)), 2)
T = pd.DataFrame([{k: v for k, v in r.items() if k != '_err'} for r in res]).sort_values('fwdMAE')
print(T.to_string(index=False))
# benchmarks
err, R = forward(F, F.pts.values.astype(float))
v = ~np.isnan(R[:, 2])
print(f'\nbenchmark: actual points as the predictor fwdMAE {err.mean():.3f} | Vegas spread MAE {np.mean(np.abs(R[v, 2] - R[v, 1])):.3f} (n={v.sum()})')
