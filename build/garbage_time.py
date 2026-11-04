"""Garbage-time filter for the box-score expected score.
Play weights (1 = competitive, 0 = garbage), faded instead of a hard cliff:
  CFB  score margin by quarter (Connelly-style cutoffs T = {Q1, Q2, Q3, Q4}); weight 1 up to T-FADE, 0 beyond T+FADE, linear between
  NFL  win probability of the offense (nflverse wp): weight 1 while the leader's WP <= LO, 0 at >= HI, linear between
A drive takes the weight of its first scrimmage play. Rates (success rate, explosive rate, available-yards share) are recomputed
from the play-by-play with and without weights; the DIFFERENCE is added to the box-score value, so the published definitions are
kept and only the garbage-time effect is applied. The drive count is unchanged (rates apply to all of a team's drives).
library: corrections(lg, D, variant) -> {(gk, team): (d_success, d_explosive, d_avail)}"""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
CFB_PKL = os.path.join(HERE, 'cfb_full/prepped_to.pkl')
NFL_PKL = os.environ.get('NFL_PBP', '/home/claude/data/pbp_new8c.pkl')
VARIANTS = {
    'cfb': {'none': None, 'c38hard': ((38, 28, 22, 16), 0), 'c38fade': ((38, 28, 22, 16), 7), 'c43fade': ((43, 37, 27, 22), 7),
            'c30fade': ((30, 24, 18, 14), 7)},
    'nfl': {'none': None, 'wp95hard': (0.95, 0.95), 'wp90_98': (0.90, 0.98), 'wp85_95': (0.85, 0.95), 'wp95_99': (0.95, 0.99)},
}

def _w_cfb(margin, period, T, fade):
    t = np.array([T[min(max(int(q), 1), 4) - 1] if q <= 4 else 999 for q in period], float)
    m = np.abs(margin)
    if fade == 0: return (m <= t).astype(float)
    return np.clip((t + fade - m) / (2 * fade), 0, 1)

def _w_nfl(wp, lo, hi):
    lead = np.maximum(wp, 1 - wp)
    if hi <= lo: return (lead < hi).astype(float)
    return np.clip((hi - lead) / (hi - lo), 0, 1)

_CACHE = {}
def plays(lg, D):
    if lg in _CACHE: return _CACHE[lg]
    if lg == 'cfb':
        p = pd.read_pickle(CFB_PKL)
        gk_of = {int(k.split('_')[1]): k for k in D['boxscores']}
        p = p[p.GameId.isin(gk_of) & p.is_rp].copy()
        p['gk'] = p.GameId.map(gk_of); p['team'] = p.Offense; p['margin'] = p.OffenseScore - p.DefenseScore; p['q'] = p.Period
        p['drive'] = p.DriveId; p['ytg'] = p.YardsToGoal; p['y'] = np.where(p.giveaway, 0, p.yds)
        p['s'] = p.succ.astype(float); p['e'] = p.expl.astype(float)
    else:
        import importlib.util
        sp = importlib.util.spec_from_file_location('ns', os.path.join(HERE, 'nfl_full', 'nfl_season.py'))
        ns = importlib.util.module_from_spec(sp); sp.loader.exec_module(ns)
        p = pd.read_pickle(NFL_PKL)
        p = p[p.game_id.isin(D['boxscores']) & ((p['pass'] == 1) | (p['rush'] == 1)) & (p.two_point_attempt != 1) & p.posteam.notna()].copy()
        p['gk'] = p.game_id; p['team'] = p.posteam.map(ns.NAME); p['q'] = p.qtr; p['drive'] = p.fixed_drive
        p['ytg'] = p.yardline_100; p['y'] = p.yards_gained.fillna(0); p['wpx'] = p.wp.fillna(0.5)
        p['s'] = (p.epa > 0).astype(float)
        ispass = (p['pass'] == 1) | (p.qb_scramble == 1)
        p['e'] = (((p['rush'] == 1) & (p.qb_scramble != 1) & (p.y >= 10)) | (ispass & (p.y >= 15))).astype(float)
    _CACHE[lg] = p
    return p

def corrections(lg, D, variant):
    return corrections_spec(lg, D, VARIANTS[lg][variant])

def corrections_spec(lg, D, spec, shrink=(0, 0)):
    """shrink = (plays, drives): the competitive-only rates are blended toward the full-game rates with this many plays /
    drives of weight, so a team with few competitive snaps (blowout from the start) isn't extrapolated from 3 drives."""
    if spec is None: return {}
    kp, kd = shrink
    p = plays(lg, D).copy()
    p['w'] = _w_cfb(p.margin.values, p.q.values, *spec) if lg == 'cfb' else _w_nfl(p.wpx.values, *spec)
    out = {}
    for (gk, t), g in p.groupby(['gk', 'team']):
        if not len(g) or g.w.sum() < 5: out[(gk, t)] = (0.0, 0.0, 0.0); continue
        W = g.w.sum(); sh = W / (W + kp) if kp else 1.0
        ds = 100 * sh * (np.average(g.s, weights=g.w) - g.s.mean())
        de = 100 * sh * (np.average(g.e, weights=g.w) - g.e.mean())
        dr = g.groupby('drive').agg(w=('w', 'first'), ytg=('ytg', 'first'), y=('y', 'sum'))
        dr = dr[dr.ytg > (9 if lg == 'cfb' else 5)]
        if lg == 'cfb':
            a_all = 100 * dr.y.sum() / dr.ytg.sum() if dr.ytg.sum() else 0
            a_w = 100 * (dr.w * dr.y).sum() / (dr.w * dr.ytg).sum() if (dr.w * dr.ytg).sum() else a_all
        else:
            r = (dr.y / dr.ytg).clip(upper=1.5)
            a_all = 100 * r.mean() if len(r) else 0
            a_w = 100 * np.average(r, weights=dr.w) if dr.w.sum() > 0 else a_all
        Wd = dr.w.sum(); shd = Wd / (Wd + kd) if kd else 1.0
        da = shd * (a_w - a_all)
        if lg == 'cfb': da = min(da, 100 - a_all)          # never above 100% of available yards
        out[(gk, t)] = (float(ds), float(de), float(da))
    return out
