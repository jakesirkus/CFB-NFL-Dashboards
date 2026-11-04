"""Per-drive yards with each play's gain capped (explosive plays partly treated as variance), from nflverse play-by-play.
Same play set as the box score (rushes + dropbacks, flags2 'is_scrim'/'yds'). Output per (game, team): list of drives
(start yards-to-goal, yards, capped yards for each CAP, first-play win probability, ended-in-turnover) in drive order.
usage: nfl_capped_yards.py OUT.pkl PBP [PBP ...]"""
import sys, os, numpy as np, pandas as pd
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'nfl_full'))
from nfl_season import flags2
CAPS = (15, 20, 25, 30, 40)

def season(path):
    p = pd.read_parquet(path) if path.endswith('.parquet') else pd.read_pickle(path)
    p = flags2(p).sort_values(['game_id', 'play_id'])
    o = p[p.is_scrim & p.posteam.notna()].copy()
    o['give'] = o.give.astype(bool)
    for c in CAPS: o[f'c{c}'] = o.yds.clip(upper=c)
    agg = {'ytg': ('yardline_100', 'first'), 'y': ('yds', 'sum'), 'wp': ('wp', 'first'), 'to': ('give', 'max'), 'n': ('yds', 'size')}
    agg.update({f'c{c}': (f'c{c}', 'sum') for c in CAPS})
    d = o.groupby(['game_id', 'posteam', 'fixed_drive'], sort=False).agg(**agg).reset_index()
    d['season'] = int(p.season.iloc[0])
    return d

if __name__ == '__main__':
    with Pool(2) as pool: res = pool.map(season, sys.argv[2:])
    D = pd.concat(res, ignore_index=True); D.to_pickle(sys.argv[1]); print(D.shape, D.season.value_counts().sort_index().to_dict())
