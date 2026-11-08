"""CFB game predictions from the user's power ratings vs the current market (Predictions tab; user approved public, Nov 8 2026).
Model (same as the user's 'Weekly Games' sheet): home spread = -(home rating - away rating + HFA), HFA = home team's value from
the workbook's Team HFA tab (neutral site: Neutral Field Adjustment, default HFA if missing); unrated/FCS team = FCS assumption;
model home win % = Normal CDF(-spread / SD).  Ratings: build/ratings/cfb.json (read_ratings.py; 'current' + 'hfa' + 'model').
Market: CollegeFootballData /lines (DraftKings current + opening spread). Edge = market spread - model spread (home perspective,
the sheet's 'Edge (Model-Vegas)' column): edge > 0 -> model likes the home team against the number, < 0 -> the away team.
usage: add_predictions.py PAGE.html WEEK GAMES.json LINES.json   (writes DATA.meta.predictions in place)"""
import sys, os, json, math, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE, WEEK, GJ, LJ = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
TAG = '<script id="dashboard-data" type="application/json">'
R = json.load(open(os.path.join(HERE, 'ratings/cfb.json')))
M = R.get('model') or {'sd': 14.0, 'defaultHfa': 3.0, 'neutralAdj': 0.0, 'fcsRating': -25.0}
T = R['teams']
def ncdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
G = json.load(open(GJ)); L = {l['id']: l for l in json.load(open(LJ))}
out = []
for g in sorted(G, key=lambda g: (g['startDate'], g['homeTeam'])):
    if not (g.get('homeClassification') == 'fbs' or g.get('awayClassification') == 'fbs'): continue
    h, a = g['homeTeam'], g['awayTeam']
    rh = T[h]['current'] if h in T else M['fcsRating']; ra = T[a]['current'] if a in T else M['fcsRating']
    neutral = bool(g.get('neutralSite'))
    hfa = M['neutralAdj'] if neutral else (T[h].get('hfa', M['defaultHfa']) if h in T else M['defaultHfa'])
    model = -(rh - ra + hfa); win = ncdf(-model / M['sd'])
    ln = next((b for b in (L.get(g['id']) or {}).get('lines', []) if b.get('spread') is not None), None)
    mk = float(ln['spread']) if ln else None
    rec = dict(id=g['id'], start=g['startDate'], tbd=bool(g.get('startTimeTBD')), home=h, away=a, neutral=neutral,
               homeConf=g.get('homeConference'), awayConf=g.get('awayConference'), confGame=bool(g.get('conferenceGame')),
               homeRating=round(rh, 2), awayRating=round(ra, 2), homeRated=h in T, awayRated=a in T, hfa=round(hfa, 2),
               model=round(model, 2), homeWin=round(100 * win, 1),
               market=mk, marketOpen=(float(ln['spreadOpen']) if ln and ln.get('spreadOpen') is not None else None),
               book=(ln['provider'] if ln else None), edge=(round(mk - model, 2) if mk is not None else None),
               completed=bool(g.get('completed')), homePoints=g.get('homePoints'), awayPoints=g.get('awayPoints'))
    out.append(rec)
s = open(PAGE).read(); i = s.index(TAG) + len(TAG); j = s.index('</script>', i); D = json.loads(s[i:j])
D['meta']['predictions'] = {'week': WEEK, 'ratingsThroughWeek': R.get('lastWeekGraded'), 'model': M,
                            'updated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
                            'source': 'DraftKings via CollegeFootballData', 'games': out}
open(PAGE, 'w').write(s[:i] + json.dumps(D, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/') + s[j:])
withm = [x for x in out if x['edge'] is not None]
print(f'predictions week {WEEK}: {len(out)} games, {len(withm)} with a market line; |edge| >= 3: {sum(abs(x["edge"]) >= 3 for x in withm)}, >= 5: {sum(abs(x["edge"]) >= 5 for x in withm)}')
