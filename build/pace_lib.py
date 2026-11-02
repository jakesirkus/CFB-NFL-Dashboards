"""Snap-to-snap pace intervals for CFB / NFL (used by add_pace.py and the totals model).

Tempo = game-clock seconds from one offensive snap to the next, counted ONLY when the clock kept running between them:
  previous play a run or completed pass that ended in bounds, no penalty, no score/turnover, same drive and quarter, nothing
  logged in between (timeout, review, penalty row), outside the last 2:00 of each half, interval 3-60 s.
(Incompletions / out of bounds stop the clock, so those gaps measure play length, not tempo.)
Each interval: game key, offense, defense, quarter, offense score margin before the snap, previous play type, whether the
previous play moved the chains, and seconds."""
import re, numpy as np, pandas as pd

def _clk(t):
    m = re.match(r'\s*\((\d{1,2}):(\d{2})\)', str(t)); return int(m.group(1)) * 60 + int(m.group(2)) if m else np.nan

def cfb_intervals(prepped, gk_of):
    """prepped = prepped_to.pkl frame; gk_of = {GameId: dashboard game key} (only these games)"""
    d = prepped[prepped.GameId.isin(gk_of)].copy()
    d['_o'] = -d['clock']; d = d.sort_values(['GameId', 'DriveNumber', 'Period', '_o', 'Id'])
    d['start'] = d.PlayText.map(_clk)
    t = d.PlayText.fillna('').str.lower()
    snap = d.is_rp & ~t.str.contains('kneel|spike') & d.Down.isin([1, 2, 3, 4])
    d['snap'] = snap
    rows = []
    for gid, g in d.groupby('GameId', sort=False):
        g = g.reset_index(drop=True)
        for i in range(len(g) - 1):
            a, b = g.iloc[i], g.iloc[i + 1]
            if not (a.snap and b.snap) or a.DriveNumber != b.DriveNumber or a.Period != b.Period or a.Offense != b.Offense: continue
            if a.Period > 4 or (a.Period in (2, 4) and b.start < 120): continue
            ta = str(a.PlayText).lower()
            if not (a.is_rush or a.is_comp) or 'out of bounds' in ta or 'penalty' in ta or 'touchdown' in ta or 'fumble' in ta or a.giveaway: continue
            if np.isnan(a.start) or np.isnan(b.start): continue
            sec = a.start - b.start
            if not 3 <= sec <= 60: continue
            rows.append((gk_of[gid], a.Offense, a.Defense, int(a.Period), float((a.OffenseScore or 0) - (a.DefenseScore or 0)),
                         'run' if a.is_rush else 'pass', bool(a.YardsGained >= a.Distance), float(sec)))
    return pd.DataFrame(rows, columns=['gk', 'off', 'def', 'qtr', 'margin', 'prev', 'chains', 'sec'])

def nfl_intervals(pbp, name):
    p = pbp.sort_values(['game_id', 'play_id']).reset_index(drop=True)
    f = lambda c: p[c].fillna(0).astype(int) == 1
    p['snap'] = p.play_type.isin(['run', 'pass']) & ~f('qb_spike') & ~f('qb_kneel') & p.down.notna()
    rows = []
    for gid, g in p.groupby('game_id', sort=False):
        g = g.reset_index(drop=True)
        for i in range(len(g) - 1):
            a, b = g.iloc[i], g.iloc[i + 1]
            if not (a.snap and b.snap) or a.drive != b.drive or a.qtr != b.qtr or a.posteam != b.posteam: continue
            if a.qtr > 4 or b.half_seconds_remaining < 120: continue
            if a.play_type == 'pass' and not (a.complete_pass == 1): continue
            if a.out_of_bounds == 1 or a.penalty == 1 or a.touchdown == 1 or a.interception == 1 or a.fumble_lost == 1 or a.timeout == 1: continue
            sec = a.game_seconds_remaining - b.game_seconds_remaining
            if not 3 <= sec <= 60: continue
            rows.append((gid, name[a.posteam], name[a.defteam], int(a.qtr), float(a.score_differential or 0),
                         'run' if a.play_type == 'run' else 'pass', bool(a.first_down == 1), float(sec)))
    return pd.DataFrame(rows, columns=['gk', 'off', 'def', 'qtr', 'margin', 'prev', 'chains', 'sec'])

def situation_adjusted(iv, teams):
    """sec ~ offense + defense + margin bin x quarter + prev type + chains moved (least squares, sparse).
    Returns {team: (offense adjusted s/play, pace faced adjusted)} at the league-average situation mix."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import lsqr
    T = sorted(set(iv.off) | set(iv['def'])); ix = {t: i for i, t in enumerate(T)}; nT = len(T)
    mb = pd.cut(iv.margin, [-99, -17, -9, -1, 0, 8, 16, 99], labels=False).astype(int)
    sit = (mb * 4 + (iv.qtr - 1)).astype(int); nS = 7 * 4
    n = len(iv); r = np.arange(n)
    cols = [ix[o] for o in iv.off], [nT + ix[x] for x in iv['def']], list(2 * nT + sit)
    X = sp.csr_matrix((np.ones(3 * n), (np.concatenate([r, r, r]), np.concatenate(cols))), shape=(n, 2 * nT + nS + 2))
    X = sp.hstack([X[:, :2 * nT + nS], sp.csr_matrix((iv.prev == 'pass').astype(float).values[:, None]),
                   sp.csr_matrix(iv.chains.astype(float).values[:, None])]).tocsr()
    b = lsqr(X, iv.sec.values, damp=0.5, atol=1e-10, btol=1e-10, iter_lim=20000)[0]
    o, de, s_ = b[:nT], b[nT:2 * nT], b[2 * nT:]
    base = np.mean(X[:, 2 * nT:] @ s_)                      # average situation effect over all intervals
    mo, md = np.mean(o[[ix[t] for t in iv.off]]), np.mean(de[[ix[t] for t in iv['def']]])
    return {t: (float(base + o[ix[t]] + md), float(base + mo + de[ix[t]])) for t in teams if t in ix}
