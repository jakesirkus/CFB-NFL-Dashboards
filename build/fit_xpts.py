"""Refit / compare variants of the box-score expected score (xpts_model.json).
Rebuilds each team-game's inputs from the published pages + drive charts, so variants of available-yards % can be tested:
  A  current: all drives with a scrimmage play
  B  drives ended by a turnover within 2 plays left out of available-yards %
  C  every drive ended by a turnover left out of available-yards %
  D  C + end-of-half/game drives of <=3 plays left out (kneels, last-second heaves)
  F  (in use since Nov 3) a turnover-ended drive counts as the better of its own share and the team's average share on other drives
Each is fitted to actual points (5-fold CV) and scored on prediction: a team's average deserved margin in its OTHER games
(minus the opponent's) predicting this game's actual margin.  usage: fit_xpts.py [cfb|nfl ...] [--ppo]"""
import json, glob, sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
TAG = '<script id="dashboard-data" type="application/json">'
TO = {'Interception', 'Fumble', 'Interception (Pick-6)', 'Fumble (Defensive TD)'}
EOH = {'End of Half', 'End of Game', 'End of Regulation'}
def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x

def load(lg):
    s = open(f'{REPO}/{lg}/index.html').read(); a = s.index(TAG) + len(TAG); D = json.loads(s[a:s.index('</script>', a)])
    CH = {}
    if lg == 'cfb':
        for f in glob.glob(f'{REPO}/cfb/drivecharts/*.json'): CH.update(json.load(open(f)))
    else:
        CH = {g: v.get('driveChart') or [] for g, v in D['boxscores'].items()}
    return D, CH

def avail_adj(lg, drs, keep, pub):
    """available-yards % with some drives left out. CFB: start from the published (pooled) value and remove the left-out drives'
    yards / available yards (the box score uses scrimmage yards, slightly different from the chart's), NFL: exact rebuild."""
    if lg != 'cfb': return avail(lg, keep)
    if len(keep) == len(drs): return pub
    S = sum(100 - d['spot1'] for d in drs); Y = pub * S / 100
    ex = [d for d in drs if d not in keep]
    S2 = S - sum(100 - d['spot1'] for d in ex); Y2 = Y - sum(max(0, d['yards']) for d in ex)
    return max(0.0, 100 * Y2 / S2) if S2 > 0 else 0.0

def avail_F(lg, drs, pub):              # same rule as add_xpts.avail_noto (unrounded)
    to = [d for d in drs if d['result'] in TO]
    if not to: return pub
    if lg == 'cfb':
        S = sum(100 - d['spot1'] for d in drs); Y = pub * S / 100
        exS = sum(100 - d['spot1'] for d in to); exY = sum(max(0, d['yards']) for d in to)
        s0 = (Y - exY) / (S - exS) if S - exS > 0 else 0.0
        return max(0.0, 100 * (Y - exY + sum(max(max(0, d['yards']), s0 * (100 - d['spot1'])) for d in to)) / S) if S > 0 else 0.0
    av = [d for d in drs if 100 - d['spot1'] > 5]; ok = [d for d in av if d['result'] not in TO]
    if not av: return 0.0
    s0 = np.mean([d['yards'] / (100 - d['spot1']) for d in ok]) if ok else 0.0
    return 100 * np.mean([max(d['yards'] / (100 - d['spot1']), s0) if d['result'] in TO else d['yards'] / (100 - d['spot1']) for d in av])

def avail(lg, drs):
    if lg == 'cfb':
        den = sum(100 - d['spot1'] for d in drs); return 100 * sum(d['yards'] for d in drs) / den if den else 0.0
    av = [d for d in drs if 100 - d['spot1'] > 5]
    return 100 * np.mean([d['yards'] / (100 - d['spot1']) for d in av]) if av else 0.0

def rows(lg, D, CH, variant):
    out = []
    for gk, v in D['boxscores'].items():
        ts = [t for t in v if t != 'driveChart']
        if len(ts) != 2 or gk not in CH: continue
        for t in ts:
            o = ts[1] if t == ts[0] else ts[0]; b = v[t]
            drs = [d for d in CH[gk] if d['team'] == t and (d.get('plays') or 0) > 0 and d.get('spot1') is not None]
            keep = drs
            if variant == 'B': keep = [d for d in drs if not (d['result'] in TO and d['plays'] <= 2)]
            if variant in ('C', 'D'): keep = [d for d in drs if d['result'] not in TO]
            if variant == 'D': keep = [d for d in keep if not (d['result'] in EOH and d['plays'] <= 3)]
            if variant == 'F':
                fav = avail_F(lg, drs, V(b['drives']['availYardsPct']) or 0)
            out.append(dict(gk=gk, t=t, o=o, home=bool(b['meta']['home']), pts=b['meta']['ts'], dr=V(b['drives']['total']) or 0,
                            av=(fav if variant == 'F' else avail_adj(lg, drs, keep, V(b['drives']['availYardsPct']) or 0)), av_pub=V(b['drives']['availYardsPct']) or 0, av_cur=avail(lg, drs),
                            sr=V(b['overall']['successRate']) or 0, ex=V(b['overall']['explosiveRate']) or 0,
                            ppo=b['opportunities'].get('ppo') or 0, trips=b['opportunities'].get('trips') or 0, week=b['meta']['week']))
    return out

def X(lg, R, ppo=False):
    cols = [[1.0, r['dr'], r['dr'] * r['av'] / 100, r['dr'] * r['sr'] / 100] + ([r['dr'] * r['ex'] / 100] if lg == 'cfb' else [])
            + ([r['trips'] * r['ppo'] / 7] if ppo else []) for r in R]
    return np.array(cols), np.array([r['pts'] for r in R], float)

def cv(Xm, y, k=5, seed=0):
    idx = np.random.default_rng(seed).permutation(len(y)); err = np.zeros(len(y))
    for f in range(k):
        te = idx[f::k]; tr = np.setdiff1d(idx, te)
        b = np.linalg.lstsq(Xm[tr], y[tr], rcond=None)[0]; err[te] = np.maximum(0, Xm[te] @ b) - y[te]
    return float(np.mean(np.abs(err))), float(1 - np.mean(err ** 2) / np.var(y))

def predictive(R, xp):
    by = {}
    for r, x in zip(R, xp): by.setdefault(r['gk'], {})[r['t']] = (x, r)
    tm = {}                                             # team -> list of (gk, deserved margin)
    for gk, g in by.items():
        if len(g) != 2: continue
        (t1, (x1, r1)), (t2, (x2, r2)) = g.items()
        tm.setdefault(t1, []).append((gk, x1 - x2)); tm.setdefault(t2, []).append((gk, x2 - x1))
    P, Y = [], []
    for gk, g in by.items():
        if len(g) != 2: continue
        (t1, (x1, r1)), (t2, (x2, r2)) = g.items()
        a = [m for k, m in tm[t1] if k != gk]; b_ = [m for k, m in tm[t2] if k != gk]
        if len(a) < 3 or len(b_) < 3: continue
        P.append([np.mean(a) - np.mean(b_), 1 if r1['home'] else (-1 if r2['home'] else 0)]); Y.append(r1['pts'] - r2['pts'])
    P, Y = np.array(P), np.array(Y, float); A = np.c_[np.ones(len(P)), P]
    b = np.linalg.lstsq(A, Y, rcond=None)[0]; e = A @ b - Y
    return float(np.mean(np.abs(e))), float(np.corrcoef(P[:, 0], Y)[0, 1]), len(Y)

if __name__ == '__main__':
    lgs = [a for a in sys.argv[1:] if a in ('cfb', 'nfl')] or ['cfb', 'nfl']
    for lg in lgs:
        D, CH = load(lg)
        R0 = rows(lg, D, CH, 'A')
        ok = sum(abs(r['av_cur'] - r['av_pub']) <= 0.15 for r in R0)
        print(f'\n{lg}: {len(R0)} team-games | available-yards % rebuilt from drive charts matches the box score on {ok}/{len(R0)}')
        Xa, ya = X(lg, R0); pa = Xa @ np.linalg.lstsq(Xa, ya, rcond=None)[0]
        print(f'  actual points as the predictor:          next-game margin MAE {predictive(R0, ya)[0]:.2f}  corr {predictive(R0, ya)[1]:.3f}')
        for var in ('A', 'B', 'C', 'D', 'F'):
            for pp in ((False, True) if '--ppo' in sys.argv else (False,)):
                R = rows(lg, D, CH, var); Xm, y = X(lg, R, pp)
                b = np.linalg.lstsq(Xm, y, rcond=None)[0]; xp = np.maximum(0, Xm @ b)
                m, r2 = cv(Xm, y); pm, pc, n = predictive(R, xp)
                print(f'  {var}{"+ppo" if pp else "    "} fit MAE {m:.2f} R2 {r2:.3f} | predicts other-game margin: MAE {pm:.2f} corr {pc:.3f} (n={n}) | coef {np.round(b, 3).tolist()}')
