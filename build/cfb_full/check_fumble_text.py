"""Weekly check: scrimmage fumbles whose 'recovered by XX' text disagrees with the turnover flag
(the feed sometimes types a lost fumble as 'Fumble Recovery (Own)' or as a plain Rush, e.g. Vandy-Kentucky wk8).
Kicks/returns and NO PLAY rows are skipped. Fix real hits in flag_overrides.json (fum_lost: true + why).
usage: check_fumble_text.py [WEEK_GAMEIDS_FILE]   (default: every FBS-involved game)"""
import sys, json, re, contextlib, io, pandas as pd
sys.path.insert(0, '.')
from penalties import learn_abbr_map
P = pd.read_pickle('prepped_to.pkl'); FBS = set(json.load(open('../nfl_rebuild/cfb_team_list.json')))
ONLY = set(int(x) for x in open(sys.argv[1]).read().split()) if len(sys.argv) > 1 else None
REC = re.compile(r'recovered by\s+([A-Za-z&\.\'\-]+)')
KICK = re.compile(r'kickoff|kicks|punt|kick attempt|field goal', re.I)
OV = json.load(open('flag_overrides.json'))
out = []
for gid, g in P[P.PlayText.str.contains('fumble', case=False, na=False)].groupby('GameId'):
    if ONLY is not None and gid not in ONLY: continue
    full = P[P.GameId == gid]; h, a = full.Home.iloc[0], full.Away.iloc[0]
    if h not in FBS and a not in FBS: continue
    with contextlib.redirect_stdout(io.StringIO()): amap = learn_abbr_map(full, None, None)
    for r in g.itertuples():
        t = str(r.PlayText)
        if KICK.search(t) or 'NO PLAY' in t or str(r.Id) in OV: continue
        ms = REC.findall(t)
        if not ms: continue
        ab = ms[-1]; tm = amap.get(ab)
        if tm is None:
            known = set(amap.values())
            if len(known) == 1: tm = ({h, a} - known).pop()
            elif r.Offense.lower().replace(' ', '').startswith(ab.lower()): tm = r.Offense
            elif r.Defense.lower().replace(' ', '').startswith(ab.lower()): tm = r.Defense
        if tm is None:
            if not r.fum_lost: out.append(f'UNRESOLVED (not flagged lost - check by hand) {gid} {r.Id} "{ab}": {t[:130]}')
            continue
        if (tm == r.Defense) != bool(r.fum_lost) and not r.int and not r.fum_td and not r.st_lost:
            out.append(f'{gid} {r.Id} {r.Offense} vs {r.Defense} [{r.PlayType}] flag fum_lost={bool(r.fum_lost)} but text: recovered by {ab} ({tm}) | {t[:130]}')
print('fumble text vs flag mismatches:', len(out))
for o in out: print(' ', o)
