"""Deserved-score inputs, version 3 ("option 4", Nov 3 2026) - the user's design:
  * down-to-down success rate is the core
  * explosive plays rewarded (explosive-rate term) but long plays partly treated as variance: each play's gain counts at most CAP
    (20) yards toward the available-yards share
  * turnovers are variance in the neutral sense: a drive that ends in a turnover counts exactly what it gained (like a punt) - no
    extra penalty (field position / return points are never charged), no bonus
  * garbage time left out: rates from competitive plays/drives, blended toward the full game for small samples
    NFL: win probability fade (full weight to 90%, none at 98%); CFB: score margin by quarter (43/37/27/22 +/-7)
Available-yards share = mean over drives (starting > 5 (NFL) / > 9 (CFB) yds from the goal) of min(capped yards / yards to goal, 1).
NFL weights fitted on 2016-2025 (nfl_xpts_grid.py, leave-one-season-out tested); CFB on 2026 weeks 1-9.
Version 4 (Nov 8 2026): + yards per play with each play capped at 'yppCap' (30) yards (fixes the overrating of teams that gain
little per snap; all weights fitted >= 0 so explosives stay positive).
inputs(lg, D, pbp=None, cfg) -> {(gk, team full name): {'av':..., 'dsr':..., 'dex':..., 'ypp':...}}  (dsr/dex = garbage-time shifts to add
to the box-score success / explosive rates)"""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))

def _wp_w(wp, lo, hi):
    lead = np.maximum(wp, 1 - wp)
    return (lead < hi).astype(float) if hi <= lo else np.clip((hi - lead) / (hi - lo), 0, 1)

def _margin_w(margin, period, T, fade):
    t = np.array([T[min(max(int(q), 1), 4) - 1] if q <= 4 else 999 for q in period], float)
    m = np.abs(margin)
    return (m <= t).astype(float) if fade == 0 else np.clip((t + fade - m) / (2 * fade), 0, 1)

def _team_values(plays, drives, cap, min_ytg, kp, kd, ycap=None):
    """plays: rows with w, s, e;  drives: rows with w, ytg, yc (capped yards), n (plays), yp (yards capped at ycap)"""
    out = {}
    W = plays.w.sum(); sh = W / (W + kp) if kp else 1.0
    dsr = 100 * sh * (np.average(plays.s, weights=plays.w) - plays.s.mean()) if W > 0 else 0.0
    dex = 100 * sh * (np.average(plays.e, weights=plays.w) - plays.e.mean()) if W > 0 else 0.0
    d = drives[drives.ytg > min_ytg]
    if len(d):
        share = np.minimum(d.yc.values / d.ytg.values, 1); full = share.mean()
        Wd = d.w.sum(); comp = np.average(share, weights=d.w) if Wd > 0 else full
        av = 100 * (full + Wd / (Wd + kd) * (comp - full))
    else:
        av = 0.0
    res = {'av': float(av), 'dsr': float(dsr), 'dex': float(dex)}
    if ycap is not None:                  # v4: yards per play, each play capped at ycap, drive-weighted for garbage time
        n = drives.n.values.astype(float); yp = drives.yp.values.astype(float); w = drives.w.values
        full = yp.sum() / n.sum() if n.sum() else 0.0; Wn = (w * n).sum(); comp = (w * yp).sum() / Wn if Wn > 0 else full
        res['ypp'] = float(full + Wn / (Wn + kp) * (comp - full))
    return res

def inputs(lg, D, cfg, pbp=None):
    cap = cfg['cap']; kp, kd = cfg['shrink']
    res = {}
    if lg == 'nfl':
        sys.path.insert(0, os.path.join(HERE, 'nfl_full'))
        from nfl_season import flags2, NAME
        p = pd.read_parquet(pbp) if str(pbp).endswith('.parquet') else pd.read_pickle(pbp)
        p = p[p.game_id.isin(D['boxscores'])]
        p = flags2(p).sort_values(['game_id', 'play_id'])
        o = p[p.is_scrim & p.posteam.notna()].copy()
        lo, hi = cfg['garbage']['wp']
        o['w'] = _wp_w(o.wp.fillna(0.5).values, lo, hi); o['s'] = o.succ.astype(float); o['e'] = o.expl.astype(float)
        o['yc'] = o.yds.clip(upper=cap); yk = cfg.get('yppCap'); o['yp'] = o.yds.clip(upper=yk) if yk else 0.0
        for (gk, t), g in o.groupby(['game_id', 'posteam'], sort=False):
            dr = g.groupby('fixed_drive', sort=False).agg(ytg=('yardline_100', 'first'), yc=('yc', 'sum'), wp=('wp', 'first'), n=('yds', 'size'), yp=('yp', 'sum'))
            dr['w'] = _wp_w(dr.wp.fillna(0.5).values, lo, hi)
            res[(gk, NAME.get(t, t))] = _team_values(g, dr, cap, 5, kp, kd, yk)
    else:
        sys.path.insert(0, HERE)
        import garbage_time as G
        p = G.plays('cfb', D).copy()
        T_, fade = cfg['garbage']['cutoffs'], cfg['garbage']['fade']
        p['w'] = _margin_w(p.margin.values, p.q.values, T_, fade)
        p['yc'] = np.where(p.giveaway, 0, p.yds.clip(upper=cap)); yk = cfg.get('yppCap')
        p['yp'] = np.where(p.giveaway, 0, p.yds.clip(upper=yk)) if yk else 0.0
        for (gk, t), g in p.groupby(['gk', 'team'], sort=False):
            dr = g.groupby('drive', sort=False).agg(ytg=('ytg', 'first'), yc=('yc', 'sum'), w=('w', 'first'), n=('yds', 'size'), yp=('yp', 'sum'))
            res[(gk, t)] = _team_values(g, dr, cap, 9, kp, kd, yk)
    return res
