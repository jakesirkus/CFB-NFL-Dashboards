"""Off-schedule run rate (FantasyPoints definition) for every box score and quarter/half split.
A run is 'held off schedule' if it gains under 4 yards on 1st down or under 3 yards on 2nd/3rd/4th down, unless it
converts a first down or scores a TD. Same runs as the box's rushAtt (no kneels, no scrambles in NFL) minus 2-pt tries.
A lost fumble never counts as a conversion. Adds to box['rushing'] (and every split):
  offSchedAtt   runs considered (rushAtt minus 2-pt tries)      offSchedRuns   runs held off schedule      offSchedRate   %
Offense: lower is better. Defense (the opponent's box): higher is better. Checks the run count (incl. 2-pt tries) == rushAtt and reports any
mismatch (those games get no value). Idempotent.
usage: add_offsched.py cfb OUT_DIR PREPPED.pkl        (OUT_DIR/index.html + OUT_DIR/periods/*.json; prepped = make_tables output)
       add_offsched.py nfl IN.html OUT.html PBP.pkl"""
import sys, json, glob, pandas as pd, numpy as np
TAG = '<script id="dashboard-data" type="application/json">'
LG = sys.argv[1]
if LG == 'cfb': SRC = DST = sys.argv[2] + '/index.html'; PBP = sys.argv[3]
else: SRC, DST, PBP = sys.argv[2], sys.argv[3], sys.argv[4]
s = open(SRC).read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); D = json.loads(s[a:b])
SPLITS = {'q1': [1], 'q2': [2], 'q3': [3], 'q4': [4], 'h1': [1, 2], 'h2': [3, 4], 'thru3': [1, 2, 3]}
p = pd.read_pickle(PBP)
if LG == 'cfb':
    r = p[p.is_rush].copy()
    r['gk'] = r.GameId.astype(int).astype(str); r['team'] = r.Offense; r['q'] = r.Period.astype(int)
    yds, down, dist = r.YardsGained.astype(float), r.Down.astype(float), r.Distance.astype(float)
    fl = r.fum_lost.fillna(False).astype(bool) | r.fum_td.fillna(False).astype(bool)
    conv = ((yds >= dist) | (r.PlayType == 'Rushing Touchdown')) & ~fl
else:
    import importlib.util, os
    spec = importlib.util.spec_from_file_location('ns', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_full', 'nfl_season.py'))
    ns = importlib.util.module_from_spec(spec); spec.loader.exec_module(ns)
    p = ns.flags2(p); r = p[p.is_rush].copy()
    r['gk'] = r.game_id; r['team'] = r.posteam.map(ns.NAME); r['q'] = r.qtr.astype(int)
    f = lambda c: r[c].fillna(0).astype(int) == 1
    yds, down = r.yds.astype(float), r.down.astype(float)
    conv = (f('first_down_rush') | f('rush_touchdown')) & ~f('fumble_lost')
r['elig'] = down.notna() & (r.PlayType != 'Two Point Rush' if LG == 'cfb' else True)   # 2-pt tries: in rushAtt, not in the stat
r['off'] = (((down == 1) & (yds < 4)) | ((down >= 2) & (yds < 3))) & ~conv & r.elig
G = {k: g for k, g in r.groupby('gk')}

def fill(bx, rows, why):
    ru = bx.get('rushing')
    if ru is None: return 0
    att, off = int(rows.elig.sum()), int(rows.off.sum())
    ra = ru.get('rushAtt')
    for k in ('offSchedAtt', 'offSchedRuns', 'offSchedRate'): ru.pop(k, None)
    if ra is None or int(round(ra)) != len(rows):
        if ra: bad.append(f'{why} rushAtt {ra} vs {len(rows)}')
        return 0
    ru['offSchedAtt'] = float(att); ru['offSchedRuns'] = float(off); ru['offSchedRate'] = round(100.0 * off / att, 1) if att else None
    return 1

def gid(gk): return gk.split('_', 1)[1] if LG == 'cfb' else gk
bad = []; n = 0
for gk, v in D['boxscores'].items():
    g = G.get(gid(gk), r.iloc[0:0])
    for t, bx in v.items():
        if t == 'driveChart': continue
        rows = g[g.team == t]; n += fill(bx, rows, f'{gk} {t} full')
        for sp, pb in (bx.get('periods') or {}).items():
            n += fill(pb, rows[rows.q.isin(SPLITS[sp])], f'{gk} {t} {sp}')
shards = {}
if LG == 'cfb':
    for fn in glob.glob(sys.argv[2] + '/periods/*.json'):
        d = json.load(open(fn)); shards[fn] = d
        for gk, per in d.items():
            g = G.get(gid(gk), r.iloc[0:0])
            for sp, teams in per.items():
                for t, pb in teams.items():
                    n += fill(pb, g[(g.team == t) & g.q.isin(SPLITS[sp])], f'{gk} {t} {sp}')
# season totals on the team table: offSchedPct (own runs) / offSchedPctAllowed (opponent runs)
tot = {}
for gk, v in D['boxscores'].items():
    ts = [t for t in v if t != 'driveChart']
    for t in ts:
        ru = v[t].get('rushing') or {}
        if 'offSchedAtt' not in ru: continue
        o = [x for x in ts if x != t]
        for team, side in ((t, 'o'), (o[0] if o else None, 'd')):
            if team is None: continue
            e = tot.setdefault(team, {'o': [0, 0], 'd': [0, 0]}); e[side][0] += ru['offSchedRuns']; e[side][1] += ru['offSchedAtt']
for t, x in D['teams'].items():
    e = tot.get(t)
    x['offSchedPct'] = round(100 * e['o'][0] / e['o'][1], 3) if e and e['o'][1] else None
    x['offSchedPctAllowed'] = round(100 * e['d'][0] / e['d'][1], 3) if e and e['d'][1] else None
js = json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
open(DST, 'w').write(s[:a] + js + s[b:])
for fn, d in shards.items(): json.dump(d, open(fn, 'w'), separators=(',', ':'))
print(f'{LG} off-schedule runs: {n} team-boxes filled; {len(bad)} count mismatches (left blank)')
for x in bad[:25]: print('  ', x)
