"""Deserved-score inputs for past NFL seasons, computed with the dashboard's own box-score code (nfl_full/nfl_box.py team_box +
nfl_drives.build_drives on nflverse play-by-play), so the definitions match the live site exactly.
Per team-game: points, drives, availYardsPct, availYardsPctNoTO (turnover rule, same as add_xpts), successRate, explosiveRate, ypp,
epaPlay, plus garbage-time shifts for several win-probability fades (competitive-only rates minus all-play rates, blended toward the
full-game value with 40 plays / 6 drives of weight).
usage: nfl_hist_features.py OUT.pkl PBP.parquet [PBP.parquet ...]   (regular season + playoffs)"""
import sys, os, numpy as np, pandas as pd
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, 'nfl_full'))
from nfl_season import flags2, NAME
from nfl_box import team_box
from nfl_drives import build_drives
TO = {'Interception', 'Fumble', 'Interception (Pick-6)', 'Fumble (Defensive TD)'}
SPECS = {'wp95hard': (0.95, 0.95), 'wp90_98': (0.90, 0.98), 'wp95_99': (0.95, 0.99), 'wp85_95': (0.85, 0.95)}
KP, KD = 40, 6
def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x

def avail_noto(drs, pub):
    to = [d for d in drs if d['result'] in TO]
    if not to: return pub
    av = [d for d in drs if 100 - d['spot1'] > 5]; ok = [d for d in av if d['result'] not in TO]
    if not av: return 0.0
    s0 = sum(d['yards'] / (100 - d['spot1']) for d in ok) / len(ok) if ok else 0.0
    return 100 * sum(max(d['yards'] / (100 - d['spot1']), s0) if d['result'] in TO else d['yards'] / (100 - d['spot1']) for d in av) / len(av)

def wfun(wp, lo, hi):
    lead = np.maximum(wp, 1 - wp)
    return (lead < hi).astype(float) if hi <= lo else np.clip((hi - lead) / (hi - lo), 0, 1)

def one_game(g):
    g = g.sort_values('play_id'); home = g.home_team.iloc[0]; away = g.away_team.iloc[0]
    try:
        drives = build_drives(g)
    except Exception as e:
        return []
    chart = [{k: v for k, v in x.items() if not k.startswith('_')} for x in drives]
    fh = g.total_home_score.max(); fa = g.total_away_score.max()
    out = []
    for T, O, pts, opts in ((home, away, fh, fa), (away, home, fa, fh)):
        try:
            b = team_box(g, T, O, drives)
        except Exception:
            continue
        drs = [d for d in chart if d['team'] == NAME.get(T, T) and (d.get('plays') or 0) > 0 and d.get('spot1') is not None]
        av = V(b['drives']['availYardsPct']) or 0
        r = dict(drv=[(d['spot1'], d['yards'], d['result']) for d in drs], season=int(g.season.iloc[0]), week=int(g.week.iloc[0]), gk=g.game_id.iloc[0], t=T, o=O, home=T == home, pts=float(pts), opts=float(opts),
                 dr=V(b['drives']['total']) or 0, av=av, avnoto=avail_noto(drs, av), sr=V(b['overall']['successRate']) or 0,
                 ex=V(b['overall']['explosiveRate']) or 0, ypp=V(b['production']['ypp']) or 0, epa=V(b['production']['epaPlay']) or 0,
                 spread=float(g.spread_line.iloc[0]) if 'spread_line' in g and pd.notna(g.spread_line.iloc[0]) else np.nan)
        # garbage-time shifts on the same play set the box uses (scrimmage plays: rushes + dropbacks)
        o = g[(g.posteam == T) & g.is_scrim]
        if len(o):
            s = o.succ.astype(float).values; e = o.expl.astype(float).values; y = o.yds.astype(float).values; ep = o.epa.fillna(0).values
            wp = o.wp.fillna(0.5).values
            dd = o.groupby('fixed_drive').agg(wp=('wp', 'first'), ytg=('yardline_100', 'first'), y=('yds', 'sum'))
            dd = dd[dd.ytg > 5]; dr_ratio = (dd.y / dd.ytg).clip(upper=1.5).values
            for nm, (lo, hi) in SPECS.items():
                w = wfun(wp, lo, hi); W = w.sum(); sh = W / (W + KP)
                if W < 1: r.update({f'{nm}_{k}': 0.0 for k in ('ds', 'de', 'da', 'dy', 'dp')}); continue
                wd = wfun(dd.wp.fillna(0.5).values, lo, hi); shd = wd.sum() / (wd.sum() + KD)
                r[f'{nm}_ds'] = 100 * sh * (np.average(s, weights=w) - s.mean())
                r[f'{nm}_de'] = 100 * sh * (np.average(e, weights=w) - e.mean())
                r[f'{nm}_dy'] = sh * (np.average(y, weights=w) - y.mean())
                r[f'{nm}_dp'] = sh * (np.average(ep, weights=w) - ep.mean())
                r[f'{nm}_da'] = 100 * shd * (np.average(dr_ratio, weights=wd) - dr_ratio.mean()) if wd.sum() > 0 and len(dr_ratio) else 0.0
        out.append(r)
    return out

def season(path):
    p = pd.read_parquet(path) if path.endswith('.parquet') else pd.read_pickle(path)
    p = flags2(p)
    rows = []
    for _, g in p.groupby('game_id'): rows += one_game(g)
    return rows

if __name__ == '__main__':
    out = sys.argv[1]
    with Pool(min(len(sys.argv) - 2, os.cpu_count() or 2)) as pool:
        res = pool.map(season, sys.argv[2:])
    df = pd.DataFrame([r for x in res for r in x]); df.to_pickle(out)
    print(df.groupby('season').size().to_dict(), df.shape)
