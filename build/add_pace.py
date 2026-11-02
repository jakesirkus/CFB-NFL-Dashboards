"""Pace stats (pace_lib.py intervals) for every box score + split and for each team's season.
Box (box['pace'], also every quarter/half split):  secPlay = average running-clock seconds between snaps (tempo),
  tempoSnaps = intervals used, plays, drives, topSec = time of possession (drive chart).
Season (teams[t]):  secPlay (raw), secPlayNeutral (quarters 1-3, score within 7), secPlayAdj (situation-adjusted: regression on
  offense + defense + score margin x quarter + previous play type + chains moved, at the league-average situation mix),
  secPlayFaced / secPlayFacedAdj (tempo opponents ran against this defense), playsPG, drivesPG, playsPerDrive, topPG (seconds),
  playsAllowedPG, drivesFacedPG.  Ranks: lower seconds = faster = rank 1 (rankPace*).
Run before opp_adjust.py (it copies teams -> teamsAdj). Idempotent.
usage: add_pace.py cfb OUT_DIR PREPPED.pkl  |  add_pace.py nfl IN.html OUT.html PBP.pkl"""
import sys, os, re, json, glob, importlib.util, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pace_lib as PL
TAG = '<script id="dashboard-data" type="application/json">'
LG = sys.argv[1]
if LG == 'cfb': SRC = DST = sys.argv[2] + '/index.html'; PBP = sys.argv[3]
else: SRC, DST, PBP = sys.argv[2], sys.argv[3], sys.argv[4]
s = open(SRC).read(); a = s.index(TAG) + len(TAG); b = s.index('</script>', a); D = json.loads(s[a:b])
SPLITS = {'q1': [1], 'q2': [2], 'q3': [3], 'q4': [4], 'h1': [1, 2], 'h2': [3, 4], 'thru3': [1, 2, 3]}
def V(x): return x['value'] if isinstance(x, dict) and 'value' in x else x
if LG == 'cfb':
    gk_of = {int(k.split('_')[1]): k for k in D['boxscores']}
    IV = PL.cfb_intervals(pd.read_pickle(PBP), gk_of)
    CH = {}; [CH.update(json.load(open(f))) for f in glob.glob(sys.argv[2] + '/drivecharts/*.json')]
else:
    spec = importlib.util.spec_from_file_location('ns', os.path.join(HERE, 'nfl_full', 'nfl_season.py'))
    ns = importlib.util.module_from_spec(spec); spec.loader.exec_module(ns)
    IV = PL.nfl_intervals(pd.read_pickle(PBP), ns.NAME)
    CH = {g: v.get('driveChart') or [] for g, v in D['boxscores'].items()}
def tsec(x):
    m = re.match(r'(\d+):(\d{2})', str(x or '')); return int(m.group(1)) * 60 + int(m.group(2)) if m else 0
G = {k: g for k, g in IV.groupby('gk')}

def pace_box(bx, gk, t, qs=None):
    iv = G.get(gk, IV.iloc[0:0]); iv = iv[iv.off == t]
    if qs: iv = iv[iv.qtr.isin(qs)]
    dr = [x for x in (CH.get(gk) or []) if x['team'] == t and (qs is None or x.get('q1') in qs)]
    plays = V(bx.get('production', {}).get('scrimPlays')); drives = V(bx.get('drives', {}).get('total'))
    bx['pace'] = {'secPlay': round(float(iv.sec.mean()), 1) if len(iv) else None, 'tempoSnaps': int(len(iv)),
                  'plays': plays, 'drives': drives, 'topSec': int(sum(tsec(x.get('top')) for x in dr))}
n = 0
for gk, v in D['boxscores'].items():
    for t, bx in v.items():
        if t == 'driveChart': continue
        pace_box(bx, gk, t); n += 1
        for sp, pb in (bx.get('periods') or {}).items(): pace_box(pb, gk, t, SPLITS[sp])
shards = {}
if LG == 'cfb':
    for fn in glob.glob(sys.argv[2] + '/periods/*.json'):
        d = json.load(open(fn)); shards[fn] = d
        for gk, per in d.items():
            for sp, teams in per.items():
                for t, pb in teams.items(): pace_box(pb, gk, t, SPLITS[sp])

# ---- season ----
TEAMS = sorted(D['teams'])
adj = PL.situation_adjusted(IV, TEAMS)
neu = IV[(IV.qtr <= 3) & (IV.margin.abs() <= 7)]
raw_o, raw_d = IV.groupby('off').sec.mean(), IV.groupby('def').sec.mean(); neu_o = neu.groupby('off').sec.mean()
agg = {t: dict(g=0, plays=0, drives=0, top=0, playsA=0, drivesA=0) for t in TEAMS}
for gk, v in D['boxscores'].items():
    ts = [t for t in v if t != 'driveChart']
    if len(ts) != 2: continue
    for t in ts:
        if t not in agg: continue
        o = ts[1] if t == ts[0] else ts[0]; e = agg[t]; e['g'] += 1
        e['plays'] += V(v[t]['production']['scrimPlays']) or 0; e['drives'] += V(v[t]['drives']['total']) or 0
        e['top'] += v[t]['pace']['topSec']; e['playsA'] += V(v[o]['production']['scrimPlays']) or 0; e['drivesA'] += V(v[o]['drives']['total']) or 0
def r1(x): return None if x is None or x != x else round(float(x), 1)
for t in TEAMS:
    e = agg[t]; x = D['teams'][t]; g = e['g'] or None
    x.update({'secPlay': r1(raw_o.get(t)), 'secPlayNeutral': r1(neu_o.get(t)), 'secPlayAdj': r1(adj[t][0]) if t in adj else None,
              'secPlayFaced': r1(raw_d.get(t)), 'secPlayFacedAdj': r1(adj[t][1]) if t in adj else None,
              'playsPG': r1(e['plays'] / g) if g else None, 'drivesPG': r1(e['drives'] / g) if g else None,
              'playsPerDrive': round(e['plays'] / e['drives'], 2) if e['drives'] else None, 'topPG': int(round(e['top'] / g)) if g else None,
              'playsAllowedPG': r1(e['playsA'] / g) if g else None, 'drivesFacedPG': r1(e['drivesA'] / g) if g else None})
for k, low in (('secPlayAdj', True), ('secPlayFacedAdj', True), ('playsPG', False), ('drivesPG', False)):
    vals = {t: D['teams'][t][k] for t in TEAMS if D['teams'][t].get(k) is not None}
    for t in TEAMS:
        v_ = D['teams'][t].get(k)
        D['teams'][t].setdefault('paceRanks', {})[k] = None if v_ is None else 1 + sum(1 for u in vals.values() if (u < v_ if low else u > v_))
D['meta']['pace'] = {'intervals': int(len(IV)), 'note': ('Tempo = game-clock seconds between snaps while the clock kept running (after an in-bounds run or '
                     'completion, no penalty/score/turnover, same drive and quarter, outside the last 2:00 of a half). Adjusted = situation-neutral '
                     '(score margin x quarter, previous play type, chains moved, opponent).')}
open(DST, 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[b:])
for fn, d in shards.items(): json.dump(d, open(fn, 'w'), separators=(',', ':'))
fast = sorted((t for t in TEAMS if D['teams'][t]['secPlayAdj'] is not None), key=lambda t: D['teams'][t]['secPlayAdj'])
print(f'{LG} pace: {len(IV)} tempo intervals, {n} team-boxes; fastest {[(t, D["teams"][t]["secPlayAdj"]) for t in fast[:3]]}, slowest {[(t, D["teams"][t]["secPlayAdj"]) for t in fast[-2:]]}')
