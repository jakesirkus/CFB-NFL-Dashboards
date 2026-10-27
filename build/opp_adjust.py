"""Opponent-adjusted season stats, rankings and radar percentiles (adds DATA.teamsAdj + DATA.meta.oppAdj to a page).

Model, per stat m (game level, one row per team-game on offense; CFB: FBS-vs-FBS games only):
    y = mu + bOff*R_off + bDef*R_def + h*home + a_off + d_def + e        weighted by the play count behind y
  R_* = the user's power rating for that team for that game:  blend*(rating going into that week) + (1-blend)*(current)
  a_*, d_* = per-team offense / defense residuals (ridge-shrunk) = unit strengths the overall rating doesn't capture
Opponent effect on an offensive game:  E = bDef*(R_def - avg) + d_def  (centred);  on a defensive game: bOff*(R_off - avg) + a_off.
Adjusted season value = season value on the page + [ mean over FBS games of (y - E)  -  mean over all games of y ]
(so the page's own stat definitions are kept; FCS games and opponent strength are what change).
usage: opp_adjust.py cfb|nfl IN.html OUT.html [--blend B] [--cv]      (--cv: choose blend/lambda by cross-validation and report)"""
import sys, json, os, copy, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from opp_metrics import M, SEASON
LG, SRC, DST = sys.argv[1:4]; args = sys.argv[4:]
BLEND = float(args[args.index('--blend') + 1]) if '--blend' in args else None
TAG = '<script id="dashboard-data" type="application/json">'
s = open(SRC).read(); a0 = s.index(TAG) + len(TAG); b0 = s.index('</script>', a0); D = json.loads(s[a0:b0])
RT = json.load(open(os.path.join(HERE, f'ratings/{LG}.json')))
RATE = RT['teams']; TEAMS = sorted(D['teams']); IDX = {t: i for i, t in enumerate(TEAMS)}; N = len(TEAMS)
CUR_MEAN = np.mean([RATE[t]['current'] for t in TEAMS])

def rating(t, week, blend):
    r = RATE[t]; wk = r['wk']; prev = max([int(k) for k in wk if int(k) <= week - 1] or [0])
    return blend * wk[str(prev)] + (1 - blend) * r['current'] - CUR_MEAN

# ---------- observations ----------
OBS = {m: [] for m in M}          # (gk, week, off, def, home(+1/-1), y, w, fbs_game)
for gk, v in D['boxscores'].items():
    ts = [t for t in v if t != 'driveChart']
    if len(ts) != 2: continue
    for t in ts:
        o = ts[1] if t == ts[0] else ts[0]; b = v[t]
        if t not in D['teams'] and o not in D['teams']: continue
        fbs = t in D['teams'] and o in D['teams']
        for m, fn in M.items():
            try: y, w = fn(b)
            except (KeyError, TypeError): continue
            if y is None or not w: continue
            OBS[m].append((gk, b['meta']['week'], t, o, 1 if b['meta']['home'] else -1, float(y), float(w), fbs))

def fit(rows, blend, lam, use_r=True):
    """weighted ridge; returns (mu, bOff, bDef, h, a[N], d[N])"""
    n = len(rows); P = 4 + 2 * N
    X = np.zeros((n, P)); y = np.zeros(n); w = np.zeros(n)
    for i, (gk, wk, t, o, hm, yy, ww, _) in enumerate(rows):
        X[i, 0] = 1; X[i, 3] = hm
        if use_r: X[i, 1] = rating(t, wk, blend); X[i, 2] = rating(o, wk, blend)
        X[i, 4 + IDX[t]] = 1; X[i, 4 + N + IDX[o]] = 1; y[i] = yy; w[i] = ww
    sw = np.sqrt(w); A = X * sw[:, None]; z = y * sw
    pen = np.zeros(P); pen[4:] = lam
    if not use_r: pen[1:3] = 1e9
    A2 = np.vstack([A, np.diag(np.sqrt(pen))]); z2 = np.concatenate([z, np.zeros(P)])
    beta = np.linalg.lstsq(A2, z2, rcond=None)[0]
    return beta

def predict(beta, rows, blend, use_r=True):
    return np.array([beta[0] + (beta[1] * rating(t, wk, blend) + beta[2] * rating(o, wk, blend) if use_r else 0) + beta[3] * hm
                     + beta[4 + IDX[t]] + beta[4 + N + IDX[o]] for (gk, wk, t, o, hm, yy, ww, _) in rows])

FBS_ROWS = {m: [r for r in rows if r[7]] for m, rows in OBS.items()}
def lam_grid(m):
    med = np.median([r[6] for r in FBS_ROWS[m]]); return [med * k for k in (0.5, 1, 2, 4, 8, 16, 32)]

def cv(m, blend, use_r, folds=5, seed=0):
    rows = FBS_ROWS[m]; games = sorted({r[0] for r in rows}); rng = np.random.default_rng(seed); rng.shuffle(games)
    fold = {g: i % folds for i, g in enumerate(games)}; best = None
    var = np.average([(r[5] - np.average([q[5] for q in rows], weights=[q[6] for q in rows])) ** 2 for r in rows], weights=[r[6] for r in rows])
    for lam in lam_grid(m):
        err = 0; wt = 0
        for k in range(folds):
            tr = [r for r in rows if fold[r[0]] != k]; te = [r for r in rows if fold[r[0]] == k]
            beta = fit(tr, blend, lam, use_r); p = predict(beta, te, blend, use_r)
            ww = np.array([r[6] for r in te]); err += np.sum(ww * (np.array([r[5] for r in te]) - p) ** 2); wt += ww.sum()
        mse = err / wt / var
        if best is None or mse < best[0]: best = (mse, lam)
    return best

METRICS = [m for m in M if FBS_ROWS[m] and (m != 'dbEpa' or LG == 'nfl')]
if '--cv' in args:
    print(f'{LG}: cross-validated error (share of game-to-game variance left unexplained; lower = better)')
    configs = [('no ratings', None, False)] + [(f'ratings, blend {b}', b, True) for b in (0, 0.25, 0.5, 0.75, 1.0)]
    res = {c[0]: {} for c in configs}
    for m in METRICS:
        for name, bl, ur in configs: res[name][m] = cv(m, bl if bl is not None else 0, ur)
    for name, _, _ in configs:
        print(f'  {name:20s} mean {np.mean([res[name][m][0] for m in METRICS]):.4f}   ' + '  '.join(f'{m}:{res[name][m][0]:.3f}' for m in ('epaPlay', 'rushEpa', 'passEpa', 'explosivePct', 'ppo', 'epaPerDrive') if m in res[name]))
    json.dump({k: {m: list(v) for m, v in d.items()} for k, d in res.items()}, open(os.path.join(HERE, f'ratings/{LG}_cv.json'), 'w'))
    sys.exit()

# ---------- final fit + adjustment ----------
CVR = json.load(open(os.path.join(HERE, f'ratings/{LG}_cv.json')))
if BLEND is None:
    BLEND = min((0, 0.25, 0.5, 0.75, 1.0), key=lambda b: np.mean([CVR[f'ratings, blend {b}'][m][0] for m in METRICS]))
LAM = {m: CVR[f'ratings, blend {BLEND}'][m][1] for m in METRICS}
delta = {}; betas = {}
for m in METRICS:
    beta = fit(FBS_ROWS[m], BLEND, LAM[m]); betas[m] = (round(float(beta[1]), 5), round(float(beta[2]), 5))
    effD = lambda r: beta[2] * rating(r[3], r[1], BLEND) + beta[4 + N + IDX[r[3]]]       # what this offense's opponent (defense) does to y
    effO = lambda r: beta[1] * rating(r[2], r[1], BLEND) + beta[4 + IDX[r[2]]]           # what this defense's opponent (offense) does to y
    rows = FBS_ROWS[m]; W = np.array([r[6] for r in rows])
    cD = np.average([effD(r) for r in rows], weights=W); cO = np.average([effO(r) for r in rows], weights=W)
    for t in TEAMS:
        for side, own, eff, c in (('off', 2, effD, cD), ('def', 3, effO, cO)):
            allr = [r for r in OBS[m] if r[own] == t]; fb = [r for r in allr if r[7]]
            if not allr or not fb: continue
            raw_all = np.average([r[5] for r in allr], weights=[r[6] for r in allr])
            adj_fbs = np.average([r[5] - (eff(r) - c) for r in fb], weights=[r[6] for r in fb])
            delta[(t, side, m)] = adj_fbs - raw_all

TA = copy.deepcopy(D['teams'])
def put(t, side, m, cur):
    d = delta.get((t, side, m)); return cur if (cur is None or d is None) else round(cur + d, 3)
for t, x in TA.items():
    for m in METRICS:
        for side, rk in (('off', 'offRaw'), ('def', 'defRaw')):
            if m in x['radar'][rk]: x['radar'][rk][m] = put(t, side, m, x['radar'][rk][m])
        if m in SEASON:
            fo, fd = SEASON[m]
            if fo in x: x[fo] = put(t, 'off', m, x[fo])
            if fd and fd in x: x[fd] = put(t, 'def', m, x[fd])
    if 'thirdPctD' in x and delta.get((t, 'def', 'thirdPct')) is not None:          # stop rate = 100 - conversion rate allowed
        x['thirdPctD'] = round(x['thirdPctD'] - delta[(t, 'def', 'thirdPct')], 3)
# ranks / radar percentiles recomputed with the same direction the page already uses
def direction(vals_raw, scores):            # +1 if a higher value gets a higher score (pct) / better rank
    v = np.array(vals_raw, float); s_ = np.array(scores, float); ok = ~np.isnan(v) & ~np.isnan(s_)
    return 1 if np.corrcoef(v[ok], s_[ok])[0, 1] >= 0 else -1
R0 = D['teams']
for k in R0[TEAMS[0]]['ranks']:
    if k not in R0[TEAMS[0]]: continue
    sgn = direction([R0[t][k] for t in TEAMS], [-R0[t]['ranks'][k] for t in TEAMS])        # rank 1 = best
    vals = {t: TA[t][k] for t in TEAMS}
    for t in TEAMS: TA[t]['ranks'][k] = 1 + sum(1 for u in TEAMS if sgn * vals[u] > sgn * vals[t] + 1e-12)
for side, rk in (('off', 'offRaw'), ('def', 'defRaw')):
    for m in R0[TEAMS[0]]['radar'][rk]:
        sgn = direction([R0[t]['radar'][rk][m] for t in TEAMS], [R0[t]['radar'][side][m] for t in TEAMS])
        arr = np.array([TA[t]['radar'][rk][m] for t in TEAMS], float)
        for t in TEAMS:
            v = TA[t]['radar'][rk][m]
            TA[t]['radar'][side][m] = round(float(100 * ((sgn * arr) <= sgn * v + 1e-12).sum() / len(arr)), 1)
D['teamsAdj'] = TA
D['meta']['oppAdj'] = {'blend': BLEND, 'note': ('Opponent-adjusted using the power ratings (blend of each opponent\'s rating going into that week and its current rating) '
                       'plus a shrunk per-unit correction from the play-by-play.' + (' FBS-vs-FBS games only.' if LG == 'cfb' else '')),
                       'ratingsThroughWeek': RT['lastWeekGraded'], 'betas': betas}
js = json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
open(DST, 'w').write(s[:a0] + js + s[b0:])
print(f'{LG}: opponent adjustment written (blend {BLEND}, {len(METRICS)} stats, {len(delta)} team-side deltas)')
