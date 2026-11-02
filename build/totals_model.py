"""Totals model: projected score = (projected game possessions / 2) x opponent-adjusted points per drive.
  points per drive (team A on offense vs B):  y = mu + off_A + def_B + h*home        (ridge, weighted by drives)
      y = w * actual points/drive + (1 - w) * expected (box-score) points/drive        (w chosen by walk-forward backtest)
  game possessions (both teams' drives):      D = mu_D + pace_A + pace_B              (ridge)
usage (library): load(lg), fit(games, w, lam_o, lam_p), project(params, A, B, home), backtest(lg)
      python3 -I totals_model.py cfb|nfl   -> walk-forward backtest vs actual totals and Vegas totals"""
import json, os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
TAG = '<script id="dashboard-data" type="application/json">'
def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x

def page(lg):
    return os.path.join(HERE, 'cfb_full/out7/index.html' if lg == 'cfb' else 'nfl_full/nfl_v37.html')

def load(lg, D=None):
    if D is None:
        s = open(page(lg)).read(); a = s.index(TAG) + len(TAG); D = json.loads(s[a:s.index('</script>', a)])
    neutral, vegas = {}, {}
    if lg == 'cfb':
        if os.path.exists('/home/claude/data/cfbd/games_2026.json'):   # CFBD /games (neutral-site flags); optional
            for g in json.load(open('/home/claude/data/cfbd/games_2026.json')): neutral[str(g['id'])] = bool(g.get('neutralSite'))
        for w in range(1, 17):
            p = f'/home/claude/data/cfbd/lines_w{w}.json'
            if not os.path.exists(p): continue
            for g in json.load(open(p)):
                ou = [l['overUnder'] for l in g['lines'] if l.get('overUnder') is not None]
                if ou: vegas[str(g['id'])] = float(np.median(ou))
    else:
        gm = pd.read_csv('/home/claude/data/games.csv') if os.path.exists('/home/claude/data/games.csv') else pd.DataFrame(columns=['season'])
        gm = gm[gm.season == 2026]
        for r in gm.itertuples():
            neutral[r.game_id] = r.location == 'Neutral'
            if r.total_line == r.total_line: vegas[r.game_id] = float(r.total_line)
    G = []
    for gk, v in D['boxscores'].items():
        ts = [t for t in v if t != 'driveChart']
        if len(ts) != 2: continue
        h = next((t for t in ts if v[t]['meta']['home']), ts[0]); a = ts[1] if h == ts[0] else ts[0]
        key = gk.split('_', 1)[1] if lg == 'cfb' else gk
        bh, ba = v[h], v[a]
        G.append(dict(gk=gk, week=bh['meta']['week'], home=h, away=a, neutral=neutral.get(key, False),
                      ph=bh['meta']['ts'], pa=ba['meta']['ts'], dh=V(bh['drives']['total']) or 0, da=V(ba['drives']['total']) or 0,
                      xh=bh['meta'].get('xPts'), xa=ba['meta'].get('xPts'), vegas=vegas.get(key),
                      fbs=(h in D['teams'] and a in D['teams'])))
    return G, sorted(D['teams'])

def fit(games, w, lam_o=4.0, lam_p=4.0, fbs=None, fcs_w=1.0):
    """fbs: set of FBS teams (CFB) -> unpenalized 'offense is FCS' / 'defense is FCS' / FCS-in-game pace terms, so FCS
    opponents don't look average and inflate FBS ratings (Nov 2 fix)"""
    F = fbs is not None
    T = sorted({g['home'] for g in games} | {g['away'] for g in games}); ix = {t: i for i, t in enumerate(T)}; N = len(T)
    # points per drive rows (one per team-game on offense)
    X, y, wt = [], [], []
    for g in games:
        for o, d_, pts, x, dr, hm in ((g['home'], g['away'], g['ph'], g['xh'], g['dh'], 1), (g['away'], g['home'], g['pa'], g['xa'], g['da'], -1)):
            if not dr or x is None: continue
            row = np.zeros(4 + 2 * N); row[0] = 1; row[1] = 0 if g['neutral'] else hm
            if F: row[2] = o not in fbs; row[3] = d_ not in fbs
            row[4 + ix[o]] = 1; row[4 + N + ix[d_]] = 1
            X.append(row); y.append(w * pts / dr + (1 - w) * x / dr); wt.append(dr * (fcs_w if F and (o not in fbs or d_ not in fbs) else 1.0))
    X, y, wt = np.array(X), np.array(y), np.array(wt, float); sw = np.sqrt(wt)
    pen = np.r_[0, 0, (0 if F else 1e6), (0 if F else 1e6), np.full(2 * N, lam_o)]
    b = np.linalg.lstsq(np.vstack([X * sw[:, None], np.diag(np.sqrt(pen))]), np.r_[y * sw, np.zeros(len(pen))], rcond=None)[0]
    # possessions per game (both teams)
    Xd, yd, wd = [], [], []
    for g in games:
        if not (g['dh'] and g['da']): continue
        row = np.zeros(2 + N); row[0] = 1
        if F: row[1] = (g['home'] not in fbs) + (g['away'] not in fbs)
        row[2 + ix[g['home']]] += 1; row[2 + ix[g['away']]] += 1
        Xd.append(row); yd.append(g['dh'] + g['da']); wd.append(fcs_w if F and (g['home'] not in fbs or g['away'] not in fbs) else 1.0)
    Xd, yd, wd = np.array(Xd), np.array(yd, float), np.sqrt(np.array(wd))
    pd_ = np.r_[0, (0 if F else 1e6), np.full(N, lam_p)]
    c = np.linalg.lstsq(np.vstack([Xd * wd[:, None], np.diag(np.sqrt(pd_))]), np.r_[yd * wd, np.zeros(len(pd_))], rcond=None)[0]
    return dict(teams=T, mu=float(b[0]), h=float(b[1]), fcsOff=float(b[2]), fcsDef=float(b[3]), off={t: float(b[4 + ix[t]]) for t in T},
                dfn={t: float(b[4 + N + ix[t]]) for t in T}, muD=float(c[0]), fcsPace=float(c[1]), pace={t: float(c[2 + ix[t]]) for t in T}, w=w, calib=0.0)

def fit_rated(games, w, lam_o, lam_p, fbs, fcs_w, rfun):
    """Same as fit(), plus the user's power ratings as an anchor (Nov 2): points/drive = mu + h + bO*R_off + bD*R_def + FCS terms
    + shrunk offense/defense residuals.  rfun(team, game) -> centered rating (None for teams without one). Strength comes mostly from
    the ratings (which carry the schedule), the residuals split it into offense vs defense for the total."""
    P = fit(games, w, lam_o, lam_p, fbs=fbs, fcs_w=fcs_w)                 # pace + FCS pace terms
    T = sorted({g['home'] for g in games} | {g['away'] for g in games}); ix = {t: i for i, t in enumerate(T)}; N = len(T)
    X, y, wt = [], [], []
    for g in games:
        for o, d_, pts, x, dr, hm in ((g['home'], g['away'], g['ph'], g['xh'], g['dh'], 1), (g['away'], g['home'], g['pa'], g['xa'], g['da'], -1)):
            if not dr or x is None: continue
            ro, rd = rfun(o, g), rfun(d_, g)
            row = np.zeros(6 + 2 * N); row[0] = 1; row[1] = 0 if g['neutral'] else hm; row[2] = o not in fbs; row[3] = d_ not in fbs
            row[4] = ro or 0.0; row[5] = rd or 0.0; row[6 + ix[o]] = 1; row[6 + N + ix[d_]] = 1
            X.append(row); y.append(w * pts / dr + (1 - w) * x / dr); wt.append(dr * (fcs_w if (o not in fbs or d_ not in fbs) else 1.0))
    X, y, wt = np.array(X), np.array(y), np.array(wt, float); sw = np.sqrt(wt)
    pen = np.r_[0, 0, 0, 0, 0, 0, np.full(2 * N, lam_o)]
    b = np.linalg.lstsq(np.vstack([X * sw[:, None], np.diag(np.sqrt(pen))]), np.r_[y * sw, np.zeros(len(pen))], rcond=None)[0]
    P.update(mu=float(b[0]), h=float(b[1]), fcsOff=float(b[2]), fcsDef=float(b[3]), bO=float(b[4]), bD=float(b[5]),
             off={t: float(b[6 + ix[t]]) for t in T}, dfn={t: float(b[6 + N + ix[t]]) for t in T})
    return P

def project(P, home, away, neutral=False, rh=0.0, ra=0.0):
    hm = 0 if neutral else 1
    D = P['muD'] + P['pace'].get(home, 0) + P['pace'].get(away, 0)
    bO, bD = P.get('bO', 0.0), P.get('bD', 0.0)              # rating anchor (fit_rated); rh/ra = centered ratings
    ph = P['mu'] + P['h'] * hm + bO * rh + bD * ra + P['off'].get(home, 0) + P['dfn'].get(away, 0)
    pa = P['mu'] - P['h'] * hm + bO * ra + bD * rh + P['off'].get(away, 0) + P['dfn'].get(home, 0)
    k = P.get('calib', 0.0) / 2                              # backtest bias correction, split between the two teams
    return D / 2 * ph - k, D / 2 * pa - k, D

def backtest(lg, ws=(0, 0.25, 0.5, 0.75, 1.0), lams=((2, 2), (4, 4), (8, 4), (16, 8)), start=4, quiet=False):
    G, fbsT = load(lg)
    weeks = sorted({g['week'] for g in G})
    res = {}
    for w in ws:
        for lam in lams:
            out = []
            for wk in weeks:
                if wk < start: continue
                tr = [g for g in G if g['week'] < wk]; te = [g for g in G if g['week'] == wk and (g['fbs'] or lg == 'nfl')]
                if not te: continue
                P = fit(tr, w, *lam, fbs=set(fbsT) if lg == 'cfb' else None)
                for g in te:
                    if g['home'] not in P['off'] or g['away'] not in P['off']: continue
                    h, a, _ = project(P, g['home'], g['away'], g['neutral'])
                    out.append((g['gk'], h + a, g['ph'] + g['pa'], g['vegas'], h - a, g['ph'] - g['pa']))
            o = pd.DataFrame(out, columns=['gk', 'model', 'actual', 'vegas', 'mmargin', 'amargin'])
            res[(w, lam)] = o
    rows = []
    for (w, lam), o in res.items():
        v = o.dropna(subset=['vegas'])
        rows.append(dict(w=w, lam=lam, n=len(o), mae=(o.model - o.actual).abs().mean(), nv=len(v), mae_on_vegas_games=(v.model - v.actual).abs().mean(),
                         vegas_mae=(v.vegas - v.actual).abs().mean(), corr=np.corrcoef(o.model, o.actual)[0, 1], bias=(o.model - o.actual).mean()))
    T = pd.DataFrame(rows).sort_values('mae')
    if not quiet: print(T.round(3).to_string(index=False))
    return T, res

if __name__ == '__main__':
    lg = sys.argv[1]; T, res = backtest(lg)
    best = T.iloc[0]; o = res[(best.w, best.lam)].dropna(subset=['vegas'])
    o = o.assign(edge=o.model - o.vegas, over=o.actual > o.vegas, push=o.actual == o.vegas)
    print(f'\nbest w={best.w} lam={best.lam}: model vs Vegas O/U (games with a Vegas total, no pushes)')
    for e in (0, 2, 4, 6, 8):
        x = o[(o.edge.abs() >= e) & ~o.push]
        win = ((x.edge > 0) == x.over).sum(); print(f'  |model - Vegas| >= {e}: {win}-{len(x) - win} ({100 * win / max(1, len(x)):.1f}%)')
