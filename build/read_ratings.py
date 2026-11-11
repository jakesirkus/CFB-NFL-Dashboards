"""Read the user's weekly power ratings from their model workbooks into build/ratings/{nfl,cfb}.json.
Output per team (dashboard team names): {"wk": {"0": rating after week 0 (= preseason + wk0 adj), "1": ..., }, "current": ...}
A week-N game is played by teams rated wk[N-1] going in. Only weeks with entered adjustments are kept.
usage: read_ratings.py nfl NFL_MODEL.xlsx | read_ratings.py cfb CFB_MODEL.xlsx"""
import sys, json, re, os, warnings
warnings.filterwarnings('ignore')
import openpyxl
LG, XL = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(XL, data_only=True, read_only=True)
rows = list(wb['Power Ratings History'].iter_rows(values_only=True))
hdr = rows[3]; col = {h: i for i, h in enumerate(hdr) if h}
data = [r for r in rows[4:] if r and r[0]]
# last week with any adjustment entered
last = max([w for w in range(0, 21) if f'Wk {w} Adj' in col and any(isinstance(r[col[f'Wk {w} Adj']], (int, float)) for r in data)] + [0])
if LG == 'nfl':
    sys.path.insert(0, os.path.join(HERE, 'nfl_full')); from nfl_season import NAME
    name = lambda x: NAME.get({'LAR': 'LA', 'JAC': 'JAX', 'WSH': 'WAS'}.get(x, x))   # note rows (e.g. injury memos) -> None
    teams = set(NAME.values())
else:
    teams = set(json.load(open(os.path.join(HERE, 'nfl_rebuild/cfb_team_list.json'))))
    nm = {str(a).strip(): str(b).strip() for a, b in list(wb['Name Map'].iter_rows(values_only=True))[1:] if a and b}
    FIX = {'Miami (FL)': 'Miami', 'Hawaii': "Hawai'i", 'JMU': 'James Madison', 'USF': 'South Florida', 'ECU': 'East Carolina',
           'FAU': 'Florida Atlantic', 'WKU': 'Western Kentucky', 'App. St.': 'App State', 'FIU': 'Florida International',
           'ULM': 'UL Monroe', 'San Jose St.': 'San José State', 'UMass': 'Massachusetts',
           'Appalachian State': 'App State', 'Pitt': 'Pittsburgh', 'San Jose State': 'San José State'}
    def name(x):
        x = str(x).strip()
        for cand in (x, nm.get(x), FIX.get(x), x.replace(' St.', ' State'), (nm.get(x) or '').replace(' St.', ' State')):
            if cand and cand in teams: return cand
        return None
out = {}; miss = []
for r in data:
    t = name(r[0])
    if t is None:
        if not isinstance(r[col['Current Rating']], (int, float)): continue   # not a team row
        miss.append(r[0]); continue
    wk = {str(w): float(r[col[f'Wk {w} Rating']]) for w in range(0, last + 1) if isinstance(r[col[f'Wk {w} Rating']], (int, float))}
    out[t] = {'wk': wk, 'current': float(r[col['Current Rating']])}
extra = {}
if LG == 'cfb':      # Nov 8 2026: game-model inputs for the Predictions tab (Team HFA tab + Team Schedule Tool constants)
    hrows = list(wb['Team HFA'].iter_rows(values_only=True))[3:]
    hmiss = []
    for r in hrows:
        if not r or not r[0] or not isinstance(r[1], (int, float)): continue
        t = name(r[0])
        if t and t in out: out[t]['hfa'] = float(r[1])
        elif t is None: hmiss.append(r[0])
    tool = {str(r[4]).strip(): r[5] for r in wb['Team Schedule Tool'].iter_rows(min_row=1, max_row=12, values_only=True) if r and len(r) > 5 and r[4]}
    extra['model'] = {'sd': float(tool.get('Game Std Dev for Win Prob', 14)), 'defaultHfa': float(tool.get('Default HFA (fallback)', 3)),
                      'neutralAdj': float(tool.get('Neutral Field Adjustment', 0)), 'fcsRating': float(tool.get('Unrated/FCS SP+ Assumption', -25))}
    print('HFA rows matched', sum('hfa' in v for v in out.values()), '| unmatched HFA names', hmiss, '| model', extra['model'])
if LG == 'nfl':      # Nov 11 2026: QB adjustments (user): Weekly Games 'Injury Adj' over 2 points (all QB-centred) + season-long QB rating drops
    QB_MIN = 2.0
    wg = list(wb['Weekly Games'].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(wg) if r and r[0] == 'Week')
    gc = {h: i for i, h in enumerate(wg[hi]) if h}; ic = next(i for h, i in gc.items() if str(h).startswith('Injury Adj'))
    qbg, unm = [], []
    for r in wg[hi + 1:]:
        if not r or not isinstance(r[0], (int, float)) or not r[gc['Away Team']] or not isinstance(r[ic], (int, float)): continue
        if abs(r[ic]) <= QB_MIN: continue
        aw, hm = name(str(r[gc['Away Team']]).strip().upper()), name(str(r[gc['Home Team']]).strip().upper())
        if not aw or not hm: unm.append((r[0], r[gc['Away Team']], r[gc['Home Team']])); continue
        # '+ = helps Home': positive -> the away team was shorthanded, negative -> the home team
        qbg.append({'week': int(r[0]), 'team': aw if r[ic] > 0 else hm, 'opp': hm if r[ic] > 0 else aw, 'points': -abs(float(r[ic]))})
    qf = os.path.join(HERE, 'ratings/nfl_qb.json')      # private: season-long QB rating drops the user confirmed (team, fromWeek, points)
    qbs = json.load(open(qf)) if os.path.exists(qf) else []
    for q in qbs: q['team'] = name(q['team']) or q['team']
    extra['qbGames'] = qbg; extra['qbSeason'] = qbs
    print(f'QB adjustments: {len(qbg)} games over {QB_MIN} pts (unmatched {unm}); season-long: {[(q["team"], q["fromWeek"], q["points"]) for q in qbs]}')
json.dump({'lastWeekGraded': last, 'teams': out, **extra}, open(os.path.join(HERE, f'ratings/{LG}.json'), 'w'), indent=0)
print(f'{LG}: {len(out)} teams matched, last graded week {last}; unmatched workbook names: {miss}; dashboard teams without a rating: {sorted(teams - set(out))[:20]}')
