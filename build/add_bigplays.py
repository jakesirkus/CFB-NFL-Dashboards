"""Big plays (20+ / 30+ / 40+ yard scrimmage plays) with the play list, for every box score and quarter/half split.
Same plays and yardage as the box's explosive-play counts (CFB: YardsGained on rush/pass rows of prepped_to.pkl;
NFL: yards_gained on rush/dropback rows of the nflverse pbp, via nfl_season.flags2). Adds box['explosiveness']['bigPlays'] =
[{q, c (clock), y (yards), k ('Pass'/'Rush'/'Scramble'), td, t (play text, trimmed)}] sorted by game time; the UI counts the
20+/30+/40+ tiers and shows the list on hover. Checks: plays with 15+ (pass) / 10+ (rush) reproduce explPass/explRush.
Idempotent. usage: add_bigplays.py cfb OUT_DIR PREPPED.pkl  |  add_bigplays.py nfl IN.html OUT.html PBP.pkl"""
import sys, os, json, glob, re, importlib.util, pandas as pd
TAG = '<script id="dashboard-data" type="application/json">'
LG = sys.argv[1]
if LG == 'cfb': SRC = DST = sys.argv[2] + '/index.html'; PBP = sys.argv[3]
else: SRC, DST, PBP = sys.argv[2], sys.argv[3], sys.argv[4]
s = open(SRC).read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); D = json.loads(s[a:b])
SPLITS = {'q1': [1], 'q2': [2], 'q3': [3], 'q4': [4], 'h1': [1, 2], 'h2': [3, 4], 'thru3': [1, 2, 3]}
MIN = 20
p = pd.read_pickle(PBP)
CLK = re.compile(r'^\s*\((\d{1,2}):(\d{2})\)\s*')
def trim(t, n=125):                 # drop the leading '(mm:ss)' (shown separately) and formation words, cap the length
    t = CLK.sub('', re.sub(r'\s+', ' ', str(t)).strip())
    t = re.sub(r'^\((No Huddle, )?Shotgun\)\s*|^\(No Huddle\)\s*|^(No Huddle-)?(Shotgun|Pistol)\s+|^No Huddle\s+', '', t)
    return t if len(t) <= n else t[:n - 1].rstrip() + '…'
def clk_text(t, fb):                # play START clock from the text when present (CFB clock columns are end-of-play)
    m = CLK.match(str(t)); return f'{int(m.group(1))}:{m.group(2)}' if m else fb
if LG == 'cfb':
    r = p[p.is_rush | p.is_pass].copy()          # not penalty-typed rows (yds 0 in the box)
    r['gk'] = r.GameId.astype(int).astype(str); r['team'] = r.Offense; r['q'] = r.Period.astype(int); r['y'] = r.YardsGained.astype(float)
    r['k'] = r.is_rush.map({True: 'Rush', False: 'Pass'})
    r['c'] = r['Clock Minutes'].fillna(0).astype(int).astype(str) + ':' + r['Clock Seconds'].fillna(0).astype(int).map('{:02d}'.format)
    r['td'] = r.PlayType.isin(['Rushing Touchdown', 'Passing Touchdown'])
    r['xp'] = r.is_comp & (r.y >= 15); r['xr'] = r.is_rush & (r.y >= 10)
    r['txt'] = r.PlayText; r['ord'] = list(zip(r.Period, -r['clock'], r.Id))
else:
    spec = importlib.util.spec_from_file_location('ns', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nfl_full', 'nfl_season.py'))
    ns = importlib.util.module_from_spec(spec); spec.loader.exec_module(ns)
    p = ns.flags2(p); r = p[p.is_scrim].copy()
    r['gk'] = r.game_id; r['team'] = r.posteam.map(ns.NAME); r['q'] = r.qtr.astype(int); r['y'] = r.yds.astype(float)
    f = lambda c: r[c].fillna(0).astype(int) == 1
    r['k'] = 'Pass'; r.loc[r.is_rush, 'k'] = 'Rush'; r.loc[f('qb_scramble'), 'k'] = 'Scramble'
    r['c'] = r.time.fillna('').astype(str).str.replace(r'^0(\d):', r'\1:', regex=True)
    r['td'] = f('touchdown') & (r.td_team == r.posteam)
    r['xp'] = r.is_db & (r.y >= 15); r['xr'] = r.is_rush & (r.y >= 10)
    r['txt'] = r.desc; r['ord'] = list(zip(r.qtr, -r.game_seconds_remaining.fillna(0), r.play_id))
G = {k: g for k, g in r.groupby('gk')}
def gid(gk): return gk.split('_', 1)[1] if LG == 'cfb' else gk
bad = []
def fill(bx, rows, why):
    ex = bx.get('explosiveness')
    if ex is None: return 0
    ex.pop('bigPlays', None)
    if int(rows.xp.sum()) != int(round(ex.get('explPass') or 0)) or int(rows.xr.sum()) != int(round(ex.get('explRush') or 0)):
        bad.append(f"{why}: expl pass {ex.get('explPass')} vs {int(rows.xp.sum())}, rush {ex.get('explRush')} vs {int(rows.xr.sum())}")
    big = rows[rows.y >= MIN].sort_values('ord', key=lambda s_: s_.map(lambda x: x))
    ex['bigPlays'] = [{'q': int(x.q), 'c': clk_text(x.txt, x.c), 'y': int(x.y), 'k': x.k, 'td': bool(x.td), 't': trim(x.txt)} for x in big.itertuples()]
    return 1
n = 0
for gk, v in D['boxscores'].items():
    g = G.get(gid(gk), r.iloc[0:0])
    for t, bx in v.items():
        if t == 'driveChart': continue
        rows = g[g.team == t]; n += fill(bx, rows, f'{gk} {t} full')
        for sp, pb in (bx.get('periods') or {}).items(): n += fill(pb, rows[rows.q.isin(SPLITS[sp])], f'{gk} {t} {sp}')
shards = {}
if LG == 'cfb':
    for fn in glob.glob(sys.argv[2] + '/periods/*.json'):
        d = json.load(open(fn)); shards[fn] = d
        for gk, per in d.items():
            g = G.get(gid(gk), r.iloc[0:0])
            for sp, teams in per.items():
                for t, pb in teams.items(): n += fill(pb, g[(g.team == t) & g.q.isin(SPLITS[sp])], f'{gk} {t} {sp}')
open(DST, 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b:])
for fn, d in shards.items(): json.dump(d, open(fn, 'w'), separators=(',', ':'))
print(f'{LG} big plays: {n} team-boxes; {len(bad)} explosive-count mismatches')
for x in bad[:20]: print('  ', x)
