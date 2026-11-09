"""Per-drive field-position-neutral measures (Nov 8 2026 test: should starting field position count?).
For each (game, offense, drive) over the box score's scrimmage plays (flags2 is_scrim): start yards-to-goal, yards and 20-yd-capped
yards, first-snap win probability, ended in a turnover, plays, and EP progress = expected points after the drive's last snap minus
expected points at its first snap (nflverse ep/epa). A touchdown play counts at most 6.0 EP (no credit for finishing beyond reaching
the goal line), a turnover play counts as no change from its snap (turnovers are variance), so a short field (high starting EP)
earns little and an 80-yard march earns a lot.
usage: nfl_drive_ep.py OUT.pkl PBP [PBP ...]"""
import sys, os, numpy as np, pandas as pd
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'nfl_full'))
from nfl_season import flags2

def season(path):
    p = pd.read_parquet(path) if path.endswith('.parquet') else pd.read_pickle(path)
    p = flags2(p).sort_values(['game_id', 'play_id'])
    o = p[p.is_scrim & p.posteam.notna()].copy()
    o['give'] = o.give.astype(bool)
    ep = o.ep.astype(float); after = ep + o.epa.fillna(0).astype(float)
    after = np.where(o.touchdown.fillna(0).astype(int) == 1, np.minimum(after, 6.0), after)
    after = np.where(o.give, ep, after)
    o['ep0'] = ep; o['ep1'] = after; o['c20'] = o.yds.clip(upper=20)
    d = o.groupby(['game_id', 'posteam', 'fixed_drive'], sort=False).agg(
        ytg=('yardline_100', 'first'), y=('yds', 'sum'), c20=('c20', 'sum'), wp=('wp', 'first'), to=('give', 'max'), n=('yds', 'size'),
        ep_start=('ep0', 'first'), ep_end=('ep1', 'last')).reset_index()
    d['ep_prog'] = d.ep_end - d.ep_start
    d['season'] = int(p.season.iloc[0])
    return d

if __name__ == '__main__':
    with Pool(2) as pool: res = pool.map(season, sys.argv[2:])
    D = pd.concat(res, ignore_index=True); D.to_pickle(sys.argv[1]); print(D.shape, D.season.value_counts().sort_index().to_dict())
