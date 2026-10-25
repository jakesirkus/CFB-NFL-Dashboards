"""Regenerate full box scores (every section except meta), quarter/half splits and game-log stat
fields for already-published games, from the current tables. Used when a data fix (e.g. yardage)
changes games in earlier weeks. Percentiles use the same pools as build_week.
usage: regen_boxes.py OUT gid,gid,...   (Week 7 games are skipped: build_week rebuilds them)"""
import sys, os, json, glob, pickle, contextlib, io, numpy as np, pandas as pd
sys.path.insert(0, '.')
from boxscore import game_boxes
from multiprocessing import Pool
OUT = sys.argv[1]; GIDS = set(sys.argv[2].split(','))
df = pd.read_pickle('prepped_to.pkl'); raw = pd.read_pickle('combined_raw_fixed.pkl')
RUSH = {'Rush', 'Rushing Touchdown', 'Two Point Rush'}
PASS = {'Pass Reception', 'Pass Incompletion', 'Passing Touchdown', 'Sack', 'Interception', 'Pass Interception Return',
        'Interception Return Touchdown', 'Two Point Pass', 'Pass Completion'}
COMP = {'Pass Reception', 'Passing Touchdown'}
def jl(x): return json.loads(json.dumps(x, default=float))
def work(gid):
    g = df[df.GameId == gid]
    with contextlib.redirect_stdout(io.StringIO()): full, per, _ = game_boxes(g, g.Home.iloc[0], g.Away.iloc[0])
    return gid, (full, per)
def gamelog(gid, t):
    g = raw[raw.GameId == gid].copy(); gp = df[df.GameId == gid]
    k = g.PlayText.str.contains('kneel', case=False, na=False)
    g['is_rush'] = g.PlayType.isin(RUSH) & ~k; g['is_pass'] = g.PlayType.isin(PASS); g['is_scrim'] = g.is_rush | g.is_pass
    g['is_expl'] = (g.is_rush & (g.YardsGained >= 10)) | (g.PlayType.isin(COMP) & (g.YardsGained >= 15))
    off = g[g.Offense == t]; de = g[g.Defense == t]; os_ = off[off.is_scrim]
    orr = off[off.is_rush]; opa = off[off.is_pass]
    return {'plays': len(os_), 'ypp': round(os_.YardsGained.sum() / len(os_), 2) if len(os_) else 0,
            'exp': int(off.is_expl.sum()), 'expAllowed': int(de.is_expl.sum()),
            'rushYds': int(orr.YardsGained.sum()), 'passYds': int(opa.YardsGained.sum()),
            # game-log 'to' = giveaways - takeaways, exactly as build_week computes it (so a turnover fix reaches the game log)
            'to': (int(gp[gp.Offense == t].giveaway.sum()) + int(gp[(gp.Defense == t) & gp.st_lost].shape[0]))
                  - (int(gp[gp.Defense == t].giveaway.sum()) + int(gp[(gp.Offense == t) & gp.st_lost].shape[0]))}
if __name__ == '__main__':
    T = '<script id="dashboard-data" type="application/json">'
    s = open(OUT + '/index.html').read(); a = s.index(T) + len(T); b = s.index('</script>', a); D = json.loads(s[a:b])
    keys = {int(k.split('_')[1]): k for k in D['boxscores'] if k.split('_')[1] in GIDS and k.split('_')[0] != '7'}
    with Pool(4) as p: NEW = dict(p.map(work, list(keys)))
    # percentile pools (same as build_week), with these games' new values in place of the old ones
    P = pickle.load(open('all_boxes3.pkl', 'rb'))['res']
    if os.path.exists('boxes_added.pkl'): P.update(pickle.load(open('boxes_added.pkl', 'rb')))
    P.update({gid: (f, pr, None) for gid, (f, pr) in NEW.items()})
    SPL = ['full', 'q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'thru3']; pools = {s_: {} for s_ in SPL}
    for gid, v in P.items():
        full = v[0]; per = v[1]
        if isinstance(full, tuple) or not isinstance(full, dict): continue
        for s_ in SPL:
            for t, bx in (full if s_ == 'full' else per[s_]).items():
                for k, x in bx['overall'].items():
                    if x['value'] is not None: pools[s_].setdefault(k, []).append(x['value'])
    pools = {s_: {k: np.sort(np.array(v)) for k, v in d.items()} for s_, d in pools.items()}
    def fill(bx, s_):
        for k, v in bx['overall'].items():
            v.pop('_raw', None)
            if v['value'] is not None: arr = pools[s_][k]; v['pct'] = round(100 * np.searchsorted(arr, v['value'], side='right') / len(arr), 1)
        return bx
    n = 0
    for gid, gk in keys.items():
        full, per = NEW[gid]
        for t, bx in D['boxscores'][gk].items():
            if t == 'driveChart' or t not in full: continue
            nb = fill(jl(full[t]), 'full')
            for sec, v in nb.items(): bx[sec] = v
            for gm in D['games'].get(t, []):
                if gm['week'] == bx['meta']['week'] and gm['opp'] == bx['meta']['opp']: gm.update(gamelog(gid, t))
            n += 1
    open(OUT + '/index.html', 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s[b:])
    m = 0
    for f in glob.glob(OUT + '/periods/*.json'):
        d = json.load(open(f)); ch = False
        for gk in d:
            gid = int(gk.split('_')[1])
            if gid in NEW and gk.split('_')[0] != '7':
                per = NEW[gid][1]; d[gk] = {s_: {t: fill(jl(per[s_][t]), s_) for t in per[s_]} for s_ in per}; ch = True; m += 1
        if ch: json.dump(d, open(f, 'w'), separators=(',', ':'), default=float)
    print('box scores regenerated', n, '| split sets', m)
